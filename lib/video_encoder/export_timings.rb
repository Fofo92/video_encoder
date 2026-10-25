# frozen_string_literal: true

module VideoEncoder
  # Keeps wall-clock stage durations for the existing completed-export receipt.
  class ExportTimings
    attr_reader :entries

    def initialize(clock: -> { Process.clock_gettime(Process::CLOCK_MONOTONIC) })
      @clock = clock
      @entries = []
    end

    def measure(stage, **details)
      started = @clock.call
      succeeded = false
      result = yield
      succeeded = true
      result
    ensure
      entries << details.merge(
        stage: stage, elapsed_seconds: (@clock.call - started).round(3),
        status: succeeded ? 'done' : 'failed'
      )
    end
  end
end
