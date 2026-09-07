# frozen_string_literal: true

require 'json'
require 'pathname'

module VideoEncoder
  # Reads source paths without probing or loading their media.
  class TrimProjectSourcePaths
    def call(json)
      document = JSON.parse(json)

      validate_format(document)

      paths = case document.fetch('version')
              when 1
                version_one_paths(document)
              when TrimProjectDocument::VERSION
                version_two_paths(document)
              else
                raise_unsupported_version(document)
              end

      paths.map { |path| Pathname(path) }.uniq
    end

    private

    def version_one_paths(document)
      timeline = document.fetch('timeline')
      segment_items = timeline.select { |item| item.fetch('type') == 'segment' }

      segment_items.map { |item| item.fetch('source') }
    end

    def version_two_paths(document)
      document.fetch('sources').map do |source|
        source.fetch('path')
      end
    end

    def validate_format(document)
      format = document.fetch('format')

      return if format == TrimProjectDocument::FORMAT

      raise ArgumentError,
            "unsupported document format: #{format}"
    end

    def raise_unsupported_version(document)
      version = document.fetch('version')

      raise ArgumentError,
            "unsupported trim project version: #{version}"
    end
  end
end
