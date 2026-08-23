# frozen_string_literal: true

module VideoEncoder
  # Extracts a clocked video and DVB subtitle segment with FFmpeg.
  class FfmpegSubtitleSegmentExtractor
    DEFAULT_TRAILING_PADDING = 2

    def initialize(runner:, trailing_padding: DEFAULT_TRAILING_PADDING)
      @runner = runner
      @trailing_padding = trailing_padding
    end

    def call(
      source_path:,
      video_track:,
      subtitle_track:,
      start_time:,
      duration:,
      output_path:
    )
      runner.run(
        'ffmpeg',
        '-y',
        '-loglevel', 'warning',
        '-i', source_path.to_s,
        '-ss', format_time(start_time),
        '-t', format_time(duration + trailing_padding),
        '-map', "0:#{video_track.index}",
        '-map', "0:#{subtitle_track.index}",
        '-c', 'copy',
        '-avoid_negative_ts', 'make_zero',
        '-f', 'mpegts',
        output_path.to_s
      )
    end

    private

    attr_reader :runner, :trailing_padding

    def format_time(value)
      return value.to_i.to_s if value.to_i == value

      value.to_f.to_s
    end
  end
end
