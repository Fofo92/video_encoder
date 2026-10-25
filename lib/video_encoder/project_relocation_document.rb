# frozen_string_literal: true

require 'json'
require 'pathname'

module VideoEncoder
  class ProjectRelocationError < StandardError; end

  # Only source-reference fields are normalized; titles and arbitrary metadata
  # are not rewritten by a recursive string substitution.
  class ProjectRelocationDocument
    def initialize(path, bytes: nil)
      @path = path
      @text = bytes || File.read(path)
    end

    def bytes
      text = @text
      document = JSON.parse(text)
      unless document['format'] == 'video_encoder.trim_project' && [1, 2].include?(document['version'])
        raise ProjectRelocationError, 'Le fichier doit être un projet de montage reconnu.'
      end

      changed = false
      references(document).each do |reference, key|
        path = reference.fetch(key)
        next if Pathname(path).absolute?

        # The existing loaders resolve relative paths from the process working
        # directory. Freeze that existing reference before relocating the JSON.
        reference[key] = File.expand_path(path)
        changed = true
      end
      changed ? JSON.pretty_generate(document) : text
    end

    def sources
      references(JSON.parse(@text)).map { |reference, key| File.expand_path(reference.fetch(key)) }
    end

    private

    def references(document)
      if document['version'] == 1
        document.fetch('timeline').select { |item| item['type'] == 'segment' }.map { |item| [item, 'source'] }
      else
        document.fetch('sources').map { |source| [source, 'path'] }
      end
    end
  end
end
