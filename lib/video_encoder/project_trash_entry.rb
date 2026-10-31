# frozen_string_literal: true

require 'json'
require 'digest'
require 'time'
require_relative 'project_trash_registry'

module VideoEncoder
  # Accepts only regular, explicitly inventoried files inside one recovery directory.
  class ProjectTrashEntry
    attr_reader :directory, :entries

    def initialize(directory)
      @directory = File.expand_path(directory)
      validate_directory
      @manifest = File.join(@directory, 'manifest.json')
      validate_file(@manifest)
      raise ProjectTrashError, 'Manifeste trop volumineux.' if File.size(@manifest) > 2 * 1024 * 1024

      @bytes = File.binread(@manifest)
      @entries = JSON.parse(@bytes)
      validate_entries
    end

    def summary
      { directory: @directory, project: @entries.keys.find { |path| path.end_with?('.json') },
        deleted_at: File.mtime(@manifest).iso8601, bytes: @entries.values.sum { |path| File.size(path) },
        files: @entries.keys, token: token }
    end

    def token
      signatures = (@entries.values + [@manifest]).map do |path|
        stat = File.lstat(path)
        [path, stat.dev, stat.ino, stat.size, stat.mtime.to_r.to_s, stat.ctime.to_r.to_s]
      end
      Digest::SHA256.hexdigest(@bytes + JSON.generate(signatures))
    end

    def restore
      validate_destinations
      moved = []
      begin
        @entries.each do |original, archived|
          # link is exclusive: an existing destination can never be overwritten.
          File.link(archived, original)
          moved << original
        end
      rescue StandardError
        moved.reverse_each { |path| File.unlink(path) }
        raise
      end
      purge
    end

    def purge
      @entries.each_value { |path| File.unlink(path) }
      File.unlink(@manifest)
      Dir.rmdir(@directory)
    end

    private

    def validate_directory
      root = File.dirname(@directory)
      raise ProjectTrashError, 'Dossier de récupération non régulier.' unless
        File.directory?(@directory) && !File.symlink?(@directory) && !File.symlink?(root) &&
        File.basename(root) == '.video_encoder_trash' && File.realpath(@directory) == @directory
    end

    def validate_file(path)
      raise ProjectTrashError, "Fichier non régulier : #{path}" unless File.file?(path) && !File.symlink?(path)
    end

    def validate_entries
      raise ProjectTrashError, 'Manifeste vide ou invalide.' unless @entries.is_a?(Hash) && !@entries.empty?

      @entries.each { |original, archived| validate_pair(original, archived) }
      expected = @entries.values.map { |path| File.basename(path) } + ['manifest.json']
      raise ProjectTrashError, 'Contenu inattendu dans le dossier de récupération.' unless
        expected.uniq.size == expected.size && Dir.children(@directory).sort == expected.sort
    end

    def validate_pair(original, archived)
      raise ProjectTrashError, 'Chemin de récupération invalide.' unless
        original.is_a?(String) && archived.is_a?(String) && original.start_with?('/') &&
        File.expand_path(original) == original && File.dirname(archived) == @directory

      validate_file(archived)
    end

    def validate_destinations
      @entries.each_key do |path|
        raise ProjectTrashError, "Destination déjà présente : #{path}" if File.exist?(path) || File.symlink?(path)
        raise ProjectTrashError, "Dossier initial absent ou déplacé : #{File.dirname(path)}" unless
          File.directory?(File.dirname(path)) && File.realpath(File.dirname(path)) == File.dirname(path)
      end
    end
  end
end
