# frozen_string_literal: true

require 'open3'

module VideoEncoder
  class Verifier
    def initialize(logger:)
      @logger = logger
    end

    def verify!(file)
      cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_format',
        '-show_streams',
        file
      ]

      stdout, stderr, status = Open3.capture3(*cmd)

      @logger.info(stdout) unless stdout.empty?
      @logger.error(stderr) unless stderr.empty?

      return true if status.success?

      message = stderr.lines.reject(&:empty?).last&.strip
      message ||= "ffprobe failed (exit #{status.exitstatus})"

      raise "#{message} (exit #{status.exitstatus})"
    end
  end
end
