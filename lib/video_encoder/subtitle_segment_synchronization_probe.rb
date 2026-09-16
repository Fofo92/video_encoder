# frozen_string_literal: true

module VideoEncoder
  # Measures one subtitle segment against the rendered video timeline.
  class SubtitleSegmentSynchronizationProbe
    def initialize(
      timeline_probe:,
      correction:,
      sample_offsets_seconds: [0],
      sample_duration_seconds: 0
    )
      @timeline_probe = timeline_probe
      @correction = correction
      @sample_offsets_seconds = sample_offsets_seconds
      @sample_duration_seconds = sample_duration_seconds
    end

    def call(
      source_path:,
      source_stream_index:,
      source_start_seconds:,
      duration_seconds:,
      transport_path:,
      rendered_video_path:,
      rendered_start_seconds:
    )
      last_failure = nil

      available_offsets(duration_seconds).each do |sample_offset|
        return correction.call(
          rendered_alignment: alignment(
            source_path: source_path,
            source_stream_index: source_stream_index,
            source_start_seconds:
              source_start_seconds + sample_offset,
            rendered_path: rendered_video_path,
            rendered_start_seconds:
              rendered_start_seconds + sample_offset
          ),
          transport_alignment: alignment(
            source_path: source_path,
            source_stream_index: source_stream_index,
            source_start_seconds:
              source_start_seconds + sample_offset,
            rendered_path: transport_path,
            rendered_start_seconds: sample_offset
          )
        )
      rescue SubtitleSynchronizationCorrection::
        AlignmentUnavailable => e
        last_failure = e
      end

      raise last_failure
    end

    private

    attr_reader :correction,
                :sample_duration_seconds,
                :sample_offsets_seconds,
                :timeline_probe

    def available_offsets(duration_seconds)
      sample_offsets_seconds.select do |sample_offset|
        sample_offset.zero? ||
          sample_offset + sample_duration_seconds <=
            duration_seconds
      end
    end

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
