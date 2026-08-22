# frozen_string_literal: true

module VideoEncoder
  # Normalizes OCR-generated SubRip subtitles.
  class SrtNormalizer
    FONT_TAG = %r{</?font\b[^>]*>}i
    TIMESTAMP = /\d{2,}:\d{2}:\d{2},\d{3}/
    TIMING_LINE = /(#{TIMESTAMP}) --> (#{TIMESTAMP})/

    def call(srt, offset: 0, end_at: nil)
      offset_in_milliseconds = (offset * 1_000).round
      end_at_in_milliseconds = (end_at * 1_000).round if end_at

      entries = srt.split(/\r?\n\r?\n/).filter_map do |entry|
        normalize_entry(
          entry,
          offset_in_milliseconds,
          end_at_in_milliseconds
        )
      end

      return '' if entries.empty?

      "#{entries.join("\n\n")}\n"
    end

    private

    def normalize_entry(entry, offset, end_at)
      normalized = entry.gsub(FONT_TAG, '')
      timing = TIMING_LINE.match(normalized)

      return normalized unless timing

      start_time = parse_timestamp(timing[1]) + offset
      end_time = parse_timestamp(timing[2]) + offset
      end_time = [end_time, end_at].min if end_at

      return if end_time <= start_time

      normalized.sub(
        TIMING_LINE,
        [
          format_timestamp(start_time),
          format_timestamp(end_time)
        ].join(' --> ')
      )
    end

    def parse_timestamp(timestamp)
      hours, minutes, seconds, milliseconds =
        timestamp.split(/[:,]/).map(&:to_i)

      (hours * 3_600_000) +
        (minutes * 60_000) +
        (seconds * 1_000) +
        milliseconds
    end

    def format_timestamp(milliseconds)
      hours, remainder = milliseconds.divmod(3_600_000)
      minutes, remainder = remainder.divmod(60_000)
      seconds, milliseconds = remainder.divmod(1_000)

      format(
        '%<hours>02d:%<minutes>02d:%<seconds>02d,%<milliseconds>03d',
        hours: hours,
        minutes: minutes,
        seconds: seconds,
        milliseconds: milliseconds
      )
    end
  end
end
