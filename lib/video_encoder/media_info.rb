# frozen_string_literal: true

require 'open3'
require 'json'

module VideoEncoder
  # Retrieves media information using ffprobe.
  class MediaInfo
    def duration(path)
      read(path).duration
    end

    def read(path)
      json = probe(path)

      Media.new(
        duration: parse_duration(json),
        audio_tracks: parse_audio_tracks(json),
        video_tracks: parse_video_tracks(json),
        subtitle_tracks: parse_subtitle_tracks(json)
      )
    end

    def parse_audio_tracks(_json)
      []
    end

    def parse_video_tracks(_json)
      []
    end

    def parse_subtitle_tracks(_json)
      []
    end
    private

    def probe(path)
      stdout, stderr, status = Open3.capture3(
        'ffprobe',
        '-v', 'error',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        path.to_s
      )

      unless status.success?
        message = stderr.lines.reject(&:empty?).last&.strip
        message ||= "ffprobe failed (exit #{status.exitstatus})"

        raise message
      end

      JSON.parse(stdout)
    end
  end
end
