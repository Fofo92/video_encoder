# frozen_string_literal: true

require 'json'

module VideoEncoder
  # Writes structured export progress events for external clients.
  class ExportProgressReporter
    PREFIX = 'VIDEO_ENCODER_EXPORT_EVENT '

    def initialize(output:)
      @output = output
    end

    def call(stage:, step:, total:, **details)
      event = {
        stage: stage,
        step: step,
        total: total
      }.merge(details)

      output.puts(
        "#{PREFIX}#{JSON.generate(event)}"
      )
      output.flush
    end

    def warning(code:, message:, **details)
      event = details.merge(
        type: 'warning',
        code: code,
        message: message
      )

      output.puts(
        "#{PREFIX}#{JSON.generate(event)}"
      )
      output.flush
    end

    private

    attr_reader :output
  end
end
