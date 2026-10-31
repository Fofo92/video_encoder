# frozen_string_literal: true

require 'json'
require 'digest'
require 'fileutils'
require_relative 'project_removal_recovery'
require_relative 'project_trash_registry'

module VideoEncoder
  class ProjectRemovalError < StandardError; end

  # Reversible removal, serialized with workers through the queue database.
  class ProjectRemoval
    def initialize(database)
      @database = database
      @trash_registry = ProjectTrashRegistry.new(database)
    end

    def call(path, dependencies: false, token: nil)
      @database.transaction(mode: :immediate) do
        project, files = prepare(path, dependencies)
        digest = Digest::SHA256.hexdigest(JSON.generate(files.map { |file| [file, signature(file)] }))
        plan = { format: 'video_encoder.project_removal', version: 1, files: files, token: digest }
        token ? execute(project, files, digest, token) : plan
      end
    end

    private

    def execute(project, files, digest, token)
      raise ProjectRemovalError, 'Les fichiers ont changé : recommence la confirmation.' unless token == digest

      ProjectRemovalRecovery.new.call(project, files) do |directory|
        @trash_registry.add(File.dirname(directory))
      end
    end

    def prepare(path, dependencies)
      project = validate_project(path)
      document = read_project(project)
      rows = @database[:jobs].all
      own = rows.select { |row| canonical(row[:project_path]) == project }
      validate_idle(project, own)
      sources = source_paths(document)
      files = [project] + (dependencies ? dependency_paths(project, own, sources) : [])
      validate_files(files, sources)
      validate_usage(files, project, rows)
      [project, files]
    end

    def validate_project(path)
      project = File.expand_path(path)
      raise ProjectRemovalError, 'Le projet doit être un fichier JSON régulier.' unless
        project.end_with?('.json') && File.file?(project) && !File.symlink?(project)

      File.realpath(project)
    end

    def validate_idle(project, own)
      raise ProjectRemovalError, 'Ce projet est en cours, en attente ou reporté.' if
        own.any? { |row| %w[running queued deferred].include?(row[:status]) }

      workspace = File.join(File.dirname(project), "video_encoder_#{File.basename(project, '.json')}_workspace")
      return unless File.exist?(workspace) || File.symlink?(workspace)

      raise ProjectRemovalError, 'Un workspace existe encore : ferme et traite ce montage avant suppression.'
    end

    def canonical(path)
      return if path.nil? || path.empty?

      File.realpath(path)
    rescue Errno::ENOENT, Errno::ENOTDIR
      File.expand_path(path)
    end

    def read_project(path)
      raise ProjectRemovalError, 'Projet trop volumineux.' if File.size(path) > 2 * 1024 * 1024

      document = JSON.parse(File.read(path))
      raise ProjectRemovalError, 'Projet video_encoder non reconnu.' unless
        document.is_a?(Hash) && document['format'] == 'video_encoder.trim_project' &&
        [1, 2].include?(document['version'])

      document
    end

    def source_paths(document)
      entries = document['version'] == 1 ? document.fetch('timeline') : document.fetch('sources')
      entries.filter_map do |entry|
        path = document['version'] == 1 ? entry['source'] : entry['path']
        canonical(path) if path.is_a?(String)
      end
    end

    def dependency_paths(project, rows, sources)
      outputs = rows.filter_map { |row| row[:output_path] }
      outputs.concat(%w[.mkv .m4v .mp4].map { |extension| project.sub(/\.json\z/, extension) })
      outputs = outputs.map { |path| File.expand_path(path) }.uniq
      outputs.reject! { |path| sources.include?(canonical(path)) }
      outputs.flat_map { |path| [path, "#{path}.video_encoder-export.json"] }
             .select { |path| File.exist?(path) || File.symlink?(path) }.uniq
    end

    def validate_files(files, sources)
      files.each do |file|
        raise ProjectRemovalError, "Fichier non régulier ou lien symbolique : #{file}" unless
          File.file?(file) && !File.symlink?(file)
        raise ProjectRemovalError, 'Une capture source ne peut pas être supprimée.' if sources.include?(canonical(file))
      end
    end

    def validate_usage(files, project, rows)
      paths = files.map { |file| canonical(file) }
      rows.each do |row|
        other = canonical(row[:project_path])
        next if other == project

        raise ProjectRemovalError, 'Un fichier est référencé par une autre tâche.' if
          paths.include?(canonical(row[:output_path])) || paths.include?(other)
        next unless readable_project?(other)

        raise ProjectRemovalError, 'Un autre projet utilise un de ces fichiers comme source.' if
          source_paths(read_project(other)).intersect?(paths)
      end
    end

    def readable_project?(path)
      path && File.file?(path)
    end

    def signature(file)
      stat = File.stat(file)
      [stat.dev, stat.ino, stat.size, stat.mtime.to_r.to_s, stat.ctime.to_r.to_s]
    end
  end
end
