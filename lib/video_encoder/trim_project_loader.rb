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
      validate_version(document)
      project = TrimProject.new
      media_by_path = {}

      document.fetch('timeline').each do |item|
        add_item(project, item, media_by_path)
      end

      project
    end

    private

    attr_reader :media_probe

    def add_item(project, item, media_by_path)
      case item.fetch('type')
      when 'segment'
        project.add_segment(
          build_segment(item, media_by_path)
        )
      when 'gap'
        project.add_gap(
          Gap.new(frame_count: item.fetch('frame_count'))
        )
      else
        raise ArgumentError, "unsupported timeline item: #{item['type']}"
      end
    end

    def build_segment(item, media_by_path)
      path = item.fetch('source')
      media = media_by_path[path] ||= media_probe.read(path)

      Segment.new(
        source: media,
        start_frame: item.fetch('start_frame'),
        end_frame: item.fetch('end_frame')
      )
    end

    def validate_version(document)
      version = document.fetch('version')

      return if version == TrimProjectDocument::VERSION

      raise ArgumentError, "unsupported trim project version: #{version}"
    end

    def validate_format(document)
      format = document.fetch('format')

      return if format == TrimProjectDocument::FORMAT

      raise ArgumentError, "unsupported document format: #{format}"
    end
  end
end
