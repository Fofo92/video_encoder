# frozen_string_literal: true

require 'digest'
require 'fileutils'
require_relative 'project_relocation_document'

module VideoEncoder
  # Copies first, commits the queue changes, then removes the old paths.
  # A failure before commit leaves every original file intact.
  class ProjectRelocationFiles
    attr_reader :project_destination, :destinations, :sources

    def initialize(project, directory, rows)
      @project = project
      @directory = File.realpath(directory)
      @rows = rows
      @created = []
      @entries = []
      @committed = false
    end

    def prepare
      validate_directory
      @project_destination = File.join(@directory, File.basename(@project))
      @project_signature = signature(File.stat(@project))
      @original_project_bytes = File.binread(@project)
      document = ProjectRelocationDocument.new(@project, bytes: @original_project_bytes)
      @project_bytes = document.bytes
      outputs = output_paths - document.sources
      @destinations = [@project_destination] + outputs.map { |path| output_destination(path) }
      add(@project, @project_destination, @project_bytes)
      unless signature(File.stat(@project)) == @project_signature
        raise ProjectRelocationError, 'Le projet a changé pendant la préparation.'
      end

      outputs.select { |path| File.exist?(path) }.each { |path| add_output(path) }
      @sources = @entries.map { |entry| entry[:source] }
      validate_targets
    end

    def output_destination(path)
      File.join(@directory, File.basename(path))
    end

    def copy
      @entries.each do |entry|
        verify(entry)
        copy_entry(entry)
        verify(entry)
      end
    end

    def finish
      @committed = true
      @entries.each do |entry|
        verify(entry)
        File.unlink(entry[:source])
      rescue StandardError => e
        warn "Projet déplacé ; ancien fichier conservé : #{entry[:source]} (#{e.message})"
      end
    end

    def committed?
      @committed
    end

    def rollback
      @created.reverse_each { |path| FileUtils.rm_f(path) }
    end

    private

    def validate_directory
      raise ProjectRelocationError, 'La destination doit être un dossier.' unless File.directory?(@directory)

      raise ProjectRelocationError, 'Destination identique au dossier actuel.' if @directory == File.dirname(@project)

      workspace = File.join(File.dirname(@project), "video_encoder_#{File.basename(@project, '.json')}_workspace")
      return unless File.exist?(workspace)

      raise ProjectRelocationError, 'Un workspace existe encore : le traiter avant le déplacement.'
    end

    def output_paths
      paths = @rows.map { |row| File.expand_path(row[:output_path]) }
      paths.concat(%w[.mkv .m4v .mp4].map { |extension| @project.sub(/\.json\z/i, extension) })
      paths.uniq
    end

    def validate_targets
      targets = @entries.map { |entry| entry[:destination] }
      raise ProjectRelocationError, 'Plusieurs fichiers visent la même destination.' unless targets.uniq == targets

      @destinations.uniq.each do |path|
        next unless File.exist?(path) || File.symlink?(path)

        raise ProjectRelocationError, "Destination déjà présente : #{path}"
      end
    end

    def copy_entry(entry)
      unless entry[:bytes]
        begin
          File.link(entry[:source], entry[:destination])
          @created << entry[:destination]
          return
        rescue Errno::EXDEV
          # Different volumes require copying before the queue can be updated.
        end
      end
      File.open(entry[:destination], File::WRONLY | File::CREAT | File::EXCL, entry[:mode]) do |output|
        @created << entry[:destination]
        if entry[:bytes]
          output.write(entry[:bytes])
        else
          File.open(entry[:source], 'rb') { |input| IO.copy_stream(input, output) }
        end
        output.flush
        output.fsync
      end
      File.utime(entry[:mtime], entry[:mtime], entry[:destination]) unless entry[:bytes]
    end

    def add_output(path)
      add(path, output_destination(path))
      receipt = "#{path}.video_encoder-export.json"
      return unless File.exist?(receipt)

      document = JSON.parse(File.read(receipt))
      unless document['format'] == 'video_encoder.completed_export' && document['version'] == 1
        raise ProjectRelocationError, "Reçu non reconnu : #{receipt}"
      end

      document['previous_output_path'] = path
      document['project_path'] = @project_destination
      document['output_path'] = output_destination(path)
      document.dig('probe', 'format')&.[]=('filename', output_destination(path))
      if document['project_sha256'] == Digest::SHA256.hexdigest(@original_project_bytes)
        document['project_sha256'] = Digest::SHA256.hexdigest(@project_bytes)
      end
      add(receipt, "#{output_destination(path)}.video_encoder-export.json", JSON.pretty_generate(document))
    end

    def add(source, destination, bytes = nil)
      unless File.file?(source) && !File.symlink?(source)
        raise ProjectRelocationError,
              "Fichier non régulier : #{source}"
      end

      stat = File.stat(source)
      @entries << { source: source, destination: destination, bytes: bytes,
                    identity: signature(stat), mode: stat.mode & 0o777, mtime: stat.mtime }
    end

    def verify(entry)
      return if signature(File.stat(entry[:source])) == entry[:identity]

      raise ProjectRelocationError, "Fichier modifié pendant le déplacement : #{entry[:source]}"
    end

    def signature(stat)
      [stat.dev, stat.ino, stat.size, stat.mtime]
    end
  end
end
