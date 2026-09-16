# frozen_string_literal: true

module VideoEncoder
  # Measures one subtitle segment against the rendered video timeline.
  class SubtitleSegmentSynchronizationProbe
    def initialize(timeline_probe:, correction:)
      @timeline_probe = timeline_probe
      @correction = correction
    end

    def call(
      source_path:,
      source_stream_index:,
      source_start_seconds:,
      transport_path:,
      rendered_video_path:,
      rendered_start_seconds:
    )
      rendered_alignment = alignment(
        source_path: source_path,
        source_stream_index: source_stream_index,
        source_start_seconds: source_start_seconds,
        rendered_path: rendered_video_path,
        rendered_start_seconds: rendered_start_seconds
      )

      transport_alignment = alignment(
        source_path: source_path,
        source_stream_index: source_stream_index,
        source_start_seconds: source_start_seconds,
        rendered_path: transport_path,
        rendered_start_seconds: 0.0
      )

      correction.call(
        rendered_alignment: rendered_alignment,
        transport_alignment: transport_alignment
      )
    end

    private

    attr_reader :correction, :timeline_probe

    def alignment(
      source_path:,
      source_stream_index:,
      source_start_seconds:,
      rendered_path:,
      rendered_start_seconds:
    )
      timeline_probe.call(
        source_path: source_path,
        source_stream_index: source_stream_index,
        source_start_seconds: source_start_seconds,
        rendered_path: rendered_path,
        rendered_stream_index: 0,
        rendered_start_seconds: rendered_start_seconds
      )
    end
  end
end
