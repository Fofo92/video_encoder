# frozen_string_literal: true

module VideoEncoder
  # Decides whether CCExtractor already preserved the subtitle clock origin.
  class SubtitleOcrTimingCorrection
    class TimestampUnavailable < StandardError; end

    TIMESTAMP = /(\d{2,}):(\d{2}):(\d{2}),(\d{3})/
    FIRST_TIMING = /#{TIMESTAMP} -->/

    def initialize(
      timing_probe:,
      tolerance_seconds:
    )
      @timing_probe = timing_probe
      @tolerance_seconds = tolerance_seconds
    end

    def call(
      srt:,
      transport_path:,
      alignment_offset:
    )
      transport_start_time = timing_probe.call(
        transport_path
      )

      ocr_start_time = first_timestamp(srt)

      if ocr_start_time + tolerance_seconds >=
         transport_start_time
        return alignment_offset
      end

      (
        transport_start_time +
        alignment_offset
      ).round(3)
    end

    private

    attr_reader :timing_probe, :tolerance_seconds

    def first_timestamp(srt)
      match = FIRST_TIMING.match(srt)

      unless match
        raise TimestampUnavailable,
              'OCR subtitle timestamp is unavailable'
      end

      hours = match[1].to_i
      minutes = match[2].to_i
      seconds = match[3].to_i
      milliseconds = match[4].to_i

      (hours * 3_600) +
        (minutes * 60) +
        seconds +
        (milliseconds / 1_000.0)
    end
  end
end
