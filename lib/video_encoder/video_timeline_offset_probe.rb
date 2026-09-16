# frozen_string_literal: true

module VideoEncoder
  # Compares source and rendered video timeline positions.
  class VideoTimelineOffsetProbe
    def initialize(
      extractor:,
      correlator:,
      sample_duration_seconds:
    )
      @extractor = extractor
      @correlator = correlator
      @sample_duration_seconds = sample_duration_seconds
    end

    def call(
      source_path:,
      source_stream_index:,
      source_start_seconds:,
      rendered_path:,
      rendered_stream_index:,
      rendered_start_seconds:
    )
      source = frames(
        path: source_path,
        stream_index: source_stream_index,
        start_seconds: source_start_seconds
      )

      rendered = frames(
        path: rendered_path,
        stream_index: rendered_stream_index,
        start_seconds: rendered_start_seconds
      )

      correlator.call(
        source: source,
        rendered: rendered
      )
    end

    private

    attr_reader :correlator,
                :extractor,
                :sample_duration_seconds

    def frames(path:, stream_index:, start_seconds:)
      extractor.call(
        path: path,
        stream_index: stream_index,
        start_seconds: start_seconds,
        duration_seconds: sample_duration_seconds
      )
    end
  end
end
