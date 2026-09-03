# frozen_string_literal: true

require 'json'

module VideoEncoder
  # Rebuilds a trim project from its versioned JSON representation.
  class TrimProjectLoader
    def initialize(media_probe:)
      @media_probe = media_probe
    end

    def load(json)
      document = JSON.parse(json)

      validate_format(document)

      case document.fetch('version')
      when 1
        load_version_one(document)
      when TrimProjectDocument::VERSION
        load_version_two(document)
      else
        raise_unsupported_version(document)
      end
    end

    private

    attr_reader :media_probe

    def load_version_one(document)
      media_by_path = {}

      build_project(document.fetch('timeline')) do |item|
        path = item.fetch('source')

        media_by_path[path] ||= media_probe.read(path)
      end
    end

    def load_version_two(document)
      media_by_identifier = load_sources(
        document.fetch('sources')
      )

      build_project(document.fetch('timeline')) do |item|
        identifier = item.fetch('source_id')

        media_by_identifier.fetch(identifier) do
          raise ArgumentError,
                "unknown source identifier: #{identifier}"
        end
      end
    end

    def load_sources(sources)
      sources.each_with_object({}) do |source, media_by_identifier|
        identifier = source.fetch('id')

        if media_by_identifier.key?(identifier)
          raise ArgumentError,
                "duplicate source identifier: #{identifier}"
        end

        media_by_identifier[identifier] = media_probe.read(
          source.fetch('path')
        )
      end
    end

    def build_project(timeline)
      timeline.each_with_object(TrimProject.new) do |item, project|
        case item.fetch('type')
        when 'segment'
          project.add_segment(
            build_segment(item, yield(item))
          )
        when 'gap'
          project.add_gap(
            Gap.new(
              frame_count: item.fetch('frame_count')
            )
          )
        else
          raise ArgumentError,
                "unsupported timeline item: #{item['type']}"
        end
      end
    end

    def build_segment(item, source)
      Segment.new(
        source: source,
        start_frame: item.fetch('start_frame'),
        end_frame: item.fetch('end_frame')
      )
    end

    def raise_unsupported_version(document)
      version = document.fetch('version')

      raise ArgumentError,
            "unsupported trim project version: #{version}"
    end

    def validate_format(document)
      format = document.fetch('format')

      return if format == TrimProjectDocument::FORMAT

      raise ArgumentError,
            "unsupported document format: #{format}"
    end
  end
end
