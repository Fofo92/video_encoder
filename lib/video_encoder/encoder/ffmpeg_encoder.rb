# frozen_string_literal: true

require 'open3'

module VideoEncoder
  module Encoder
    # FFmpegEncoder encodes video files using ffmpeg.
    class FFmpegEncoder < Base
      def encode(job)
        source = job.source.to_s
        output = source.sub(/\.[^.]+$/, '.mp4')

        cmd = [
          'ffmpeg',
          '-y',
          '-i', source,
          '-c:v', 'libx264',
          '-preset', 'medium',
          '-crf', '22',
          '-c:a', 'aac',
          output
        ]

        @logger.info(cmd.join(' '))
        stdout, stderr, status = Open3.capture3(*cmd)

        @logger.info(stdout) unless stdout.empty?
        @logger.error(stderr) unless stderr.empty?

        return if status.success?

        message = stderr.lines.reject(&:empty?).last&.strip
        message ||= "ffmpeg failed (exit #{status.exitstatus})"

        raise "#{message} (exit #{status.exitstatus})"
      end
    end
  end
end
