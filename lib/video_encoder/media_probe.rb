# frozen_string_literal: true

require 'open3'
require 'json'

module VideoEncoder
  # Retrieves media information using ffprobe.
  class MediaProbe
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

    private

    def parse_duration(json)
      json.dig('format', 'duration').to_f
    end

    def parse_audio_tracks(json)
      parse_tracks(json, 'audio')
    end

    def parse_video_tracks(json)
      parse_tracks(json, 'video')
    end

    def parse_subtitle_tracks(json)
      parse_tracks(json, 'subtitle')
    end

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

    def parse_tracks(json, type)
      json.fetch('streams', [])
          .select { |stream| stream['codec_type'] == type }
          .map do |stream|
            Track.new(
              index: stream['index'],
              type: type.to_sym,
              codec: stream['codec_name'],
              language: stream.dig('tags', 'language'),
              default: stream.dig('disposition', 'default') == 1,
              forced: stream.dig('disposition', 'forced') == 1,
              hearing_impaired:
                stream.dig('disposition', 'hearing_impaired') == 1,
              visual_impaired:
                stream.dig('disposition', 'visual_impaired') == 1
            )
          end
    end
  end
end
