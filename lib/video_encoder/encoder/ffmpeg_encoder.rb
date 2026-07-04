# frozen_string_literal: true

require 'open3'

module VideoEncoder
  module Encoder
    # FFmpegEncoder encodes video files using ffmpeg.
    class FFmpegEncoder < Base
      def initialize(logger: $stdout)
        @logger = logger
      end

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

        @logger.puts(cmd.join(' '))

        stdout, stderr, status = Open3.capture3(*cmd)

        @logger.puts(stdout) unless stdout.empty?

        unless status.success?
          raise <<~ERROR
            ffmpeg failed (exit #{status.exitstatus})

            #{stderr}
          ERROR
        end
      end
    end
  end
end
