# frozen_string_literal: true

require 'json'

module VideoEncoder
  # Serializes a trim project into its versioned JSON representation.
  class TrimProjectSerializer
    def dump(project)
      JSON.generate(
        format: TrimProjectDocument::FORMAT,
        version: TrimProjectDocument::VERSION,
        timeline: project.timeline.map { |item| serialize(item) }
      )
    end

    private

    def serialize(item)
      case item
      when Segment
        serialize_segment(item)
      when Gap
        {
          type: 'gap',
          frame_count: item.frame_count
        }
      else
        raise ArgumentError, "unsupported timeline item: #{item.class}"
      end
    end

    def serialize_segment(segment)
      unless segment.start_frame && segment.end_frame
        raise ArgumentError, 'persistent segments require frame boundaries'
      end

      {
        type: 'segment',
        source: segment.source.path.to_s,
        start_frame: segment.start_frame,
        end_frame: segment.end_frame
      }
    end
  end
end
