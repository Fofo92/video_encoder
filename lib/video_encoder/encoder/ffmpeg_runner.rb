# frozen_string_literal: true

require 'open3'

module VideoEncoder
  module Encoder
    class FFmpegRunner
      def initialize(logger:)
        @logger = logger
      end

      def run(cmd)
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
