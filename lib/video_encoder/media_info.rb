# frozen_string_literal: true

require 'open3'

module VideoEncoder
  # Retrieves media information using ffprobe.
  class MediaInfo
    def duration(path)
      stdout, stderr, status = Open3.capture3(
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path.to_s
      )

      return Float(stdout.strip) if status.success?

      message = stderr.lines.reject(&:empty?).last&.strip
      message ||= "ffprobe failed (exit #{status.exitstatus})"

      raise RuntimeError, message
    end
  end
end
