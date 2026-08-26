# frozen_string_literal: true

require 'open3'

module VideoEncoder
  # Verifies that an external command can run successfully.
  class ExternalCommandProbe
    def initialize(capture: Open3.method(:capture3))
      @capture = capture
    end

    def call(executable, *)
      _stdout, stderr, status = capture.call(
        executable,
        *
      )

      return if status.success?

      raise MissingExternalDependenciesError,
            failure_message(executable, stderr)
    rescue Errno::ENOENT
      raise MissingExternalDependenciesError,
            "external dependency unavailable: #{executable}"
    end

    private

    attr_reader :capture

    def failure_message(executable, stderr)
      details = stderr.strip
      message = "external dependency unavailable: #{executable}"

      return message if details.empty?

      "#{message}: #{details}"
    end
  end
end
