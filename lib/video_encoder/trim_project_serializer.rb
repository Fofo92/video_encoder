# frozen_string_literal: true

require 'json'

module VideoEncoder
  # Serializes a trim project into its versioned JSON representation.
  class TrimProjectSerializer
    def initialize(
      inspection_serializer: MediaInspectionSerializer.new
    )
      @inspection_serializer = inspection_serializer
    end

    def dump(project)
      sources = project_sources(project)
      source_ids = build_source_ids(sources)

      JSON.generate(
        format: TrimProjectDocument::FORMAT,
        version: TrimProjectDocument::VERSION,
        sources: sources.map do |source|
          serialize_source(
            source,
            source_ids.fetch(source)
          )
        end,
        timeline: project.timeline.map do |item|
          serialize(item, source_ids)
        end
      )
    end

    private

    attr_reader :inspection_serializer

    def project_sources(project)
      project.timeline.filter_map do |item|
        item.source if item.is_a?(Segment)
      end.uniq
    end

    def build_source_ids(sources)
      sources.each_with_index.to_h do |source, index|
        identifier = (
          index.zero? ? 'source' : "source_#{index}"
        )

        [source, identifier]
      end
    end

    def serialize_source(source, identifier)
      {
        id: identifier,
        path: source.path.to_s,
        inspection: inspection_serializer.call(source)
      }
    end

    def serialize(item, source_ids)
      case item
      when Segment
        serialize_segment(item, source_ids)
      when Gap
        {
          type: 'gap',
          frame_count: item.frame_count
        }
      else
        raise ArgumentError,
              "unsupported timeline item: #{item.class}"
      end
    end

    def serialize_segment(segment, source_ids)
      unless segment.start_frame && segment.end_frame
        raise ArgumentError,
              'persistent segments require frame boundaries'
      end

      {
        type: 'segment',
        source_id: source_ids.fetch(segment.source),
        start_frame: segment.start_frame,
        end_frame: segment.end_frame
      }
    end
  end
end
