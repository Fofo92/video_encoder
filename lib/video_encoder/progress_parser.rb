# frozen_string_literal: true

module VideoEncoder
  # Parses ffmpeg progress output.
  class ProgressParser
    PREFIX = 'out_time_ms='

    def parse(line)
      return unless line.start_with?(PREFIX)

      line.delete_prefix(PREFIX).to_i / 1_000_000.0
    end
  end
end
