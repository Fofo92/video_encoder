# frozen_string_literal: true

module VideoEncoder
  # Monitors FFmpeg output and reports encoding progress.
  class EncodingMonitor
    def initialize(parser:, progress:, reporter:)
      @parser = parser
      @progress = progress
      @reporter = reporter
    end

    def call(_stream, line)
      seconds = @parser.parse(line)
      return unless seconds

      @reporter.update(@progress.percent(seconds))
    end

    def finish
      @reporter.finish
    end
  end
end
