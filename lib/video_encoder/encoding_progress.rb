# frozen_string_literal: true

module VideoEncoder
  # Computes encoding progress from elapsed and total duration.
  class EncodingProgress
    def initialize(total_duration)
      @total_duration = total_duration.to_f
    end

    def percent(elapsed)
      return 100 if @total_duration <= 0

      value = (elapsed.to_f * 100 / @total_duration).round

      [[value, 0].max, 100].min
    end
  end
end
