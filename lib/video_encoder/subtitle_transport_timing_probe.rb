# frozen_string_literal: true

require 'json'
require 'open3'

module VideoEncoder
  # Reads the subtitle clock origin of an intermediate transport.
  class SubtitleTransportTimingProbe
    class TimestampUnavailable < StandardError; end

    def initialize(executor: Open3)
      @executor = executor
    end

    def call(path)
      command = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 's:0',
        '-show_entries', 'stream=start_time',
        '-of', 'json',
        path.to_s
      ]

      output, diagnostic, status = executor.capture3(*command)

      unless status.success?
        failure = CommandRunner::CommandFailed.new(
          command: command,
          status: status
        )

        raise failure,
              "#{failure.message}\n#{diagnostic}"
      end

      document = JSON.parse(output)
      stream = document.fetch('streams').first
      timestamp = stream&.fetch('start_time', nil)

      unless timestamp
        raise TimestampUnavailable,
              'subtitle timestamp is unavailable'
      end

      Float(timestamp)
    end

    private

    attr_reader :executor
  end
end
