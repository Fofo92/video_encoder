# frozen_string_literal: true

require 'json'
require 'digest'
require 'time'

module VideoEncoder
  class QuarantinePolicyError < StandardError; end

  # Bounded metadata reads and exact identities; media files are never hashed.
  module QuarantineFiles
    module_function

    def regular(path)
      raise QuarantinePolicyError, "Fichier absent ou lien symbolique : #{path}" unless
        path.is_a?(String) && path.start_with?('/') && File.file?(path) && !File.symlink?(path)

      File.realpath(path)
    end

    def signature(path)
      stat = File.stat(regular(path))
      [stat.dev, stat.ino, stat.size, stat.mtime.to_r.to_s]
    end

    def bytes(path)
      regular(path)
      raise QuarantinePolicyError, "Métadonnées trop volumineuses : #{path}" if File.size(path) > 2 * 1024 * 1024

      File.binread(path)
    end

    def document(path)
      result = JSON.parse(bytes(path))
      raise QuarantinePolicyError, "Document invalide : #{path}" unless result.is_a?(Hash)

      result
    end

    def sources(path)
      data = document(path)
      raise QuarantinePolicyError, 'Projet non reconnu.' unless data['format'] == 'video_encoder.trim_project'

      source_items(data).map do |source|
        raise QuarantinePolicyError, 'Chemin source non absolu.' unless source.is_a?(String) && source.start_with?('/')

        File.expand_path(source)
      end.uniq
    end

    def source_items(data)
      case data['version']
      when 1
        data.fetch('timeline').select { |item| item.fetch('type') == 'segment' }.map { |item| item.fetch('source') }
      when 2
        data.fetch('sources').map { |item| item.fetch('path') }
      else
        raise QuarantinePolicyError, 'Version de projet inconnue.'
      end
    end
  end
end
