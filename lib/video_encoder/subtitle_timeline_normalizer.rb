# frozen_string_literal: true

module VideoEncoder
  # Applies segment-specific offsets to one OCR-generated SRT timeline.
  class SubtitleTimelineNormalizer
    def initialize(normalizer:, composer:)
      @normalizer = normalizer
      @composer = composer
    end

    def call(srt, timeline_start:, segments:)
      input_start = 0

      normalized_segments = segments.map do |segment|
        duration = segment.fetch(:duration)
        input_end = input_start + duration

        output_start = timeline_start + input_start
        output_end = timeline_start + input_end

        normalized = normalizer.call(
          srt,
          offset:
            timeline_start +
            segment.fetch(:offset_seconds),
          input_start_at: input_start,
          input_end_at: input_end,
          start_at: output_start,
          end_at: output_end
        )

        input_start = input_end
        normalized
      end

      composer.call(normalized_segments)
    end

    private

    attr_reader :composer, :normalizer
  end
end
