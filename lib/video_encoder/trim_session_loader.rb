# frozen_string_literal: true

require 'json'

module VideoEncoder
  # Builds a trim project from the editing session produced by the UI.
  class TrimSessionLoader
    FORMAT = 'video_encoder.trim_session'
    VERSION = 1

    def initialize(media_probe:)
      @media_probe = media_probe
    end

    def load(json)
      document = JSON.parse(json)

      validate_document(document)

      media_by_identifier = load_sources(
        document.fetch('sources')
      )

      build_project(
        document.fetch('timeline'),
        media_by_identifier
      )
    end

    private

    attr_reader :media_probe

    def load_sources(sources)
      sources.each_with_object({}) do |source, media_by_identifier|
        identifier = source.fetch('id')
        path = source.fetch('path')

        raise ArgumentError, "duplicate source identifier: #{identifier}" if media_by_identifier.key?(identifier)

        media_by_identifier[identifier] = media_probe.read(path)
      end
    end

    def build_project(timeline, media_by_identifier)
      timeline.each_with_object(TrimProject.new) do |item, project|
        source_identifier = item.fetch('source_id')

        source = media_by_identifier.fetch(source_identifier) do
          raise ArgumentError, "unknown source identifier: #{source_identifier}"
        end

        project.add_segment(
          Segment.new(
            source: source,
            start_frame: item.fetch('start_frame'),
            end_frame: item.fetch('end_frame')
          )
        )
      end
    end

    def validate_document(document)
      format = document.fetch('format')
      version = document.fetch('version')

      raise ArgumentError, "unsupported trim session format: #{format}" unless format == FORMAT

      return if version == VERSION

      raise ArgumentError, "unsupported trim session version: #{version}"
    end
  end
end
