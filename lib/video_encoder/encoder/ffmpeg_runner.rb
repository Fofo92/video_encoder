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

        stdout_data = String.new
        stderr_data = String.new

        Open3.popen3(*cmd) do |_stdin, stdout, stderr, wait_thr|

          out_thread = Thread.new do
            stdout.each_line do |line|
              stdout_data << line
              yield(:stdout, line) if block_given?
            end
          end

          err_thread = Thread.new do
            stderr.each_line do |line|
              stderr_data << line
              yield(:stderr, line) if block_given?
            end
          end

          out_thread.join
          err_thread.join

          status = wait_thr.value

          @logger.info(stdout_data) unless stdout_data.empty?
          @logger.error(stderr_data) unless stderr_data.empty?

          return if status.success?
          message = last_error(stderr_data, status)

          raise RuntimeError, message
        end
      end

      private

      def last_error(stderr_data, status)
        message = stderr_data.lines.reject(&:empty?).last&.strip
        message ||= "ffmpeg failed"

        "#{message} (exit #{status.exitstatus})"
      end
    end
  end
end
