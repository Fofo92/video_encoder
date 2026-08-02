# frozen_string_literal: true

module VideoEncoder
  # Represents a video segment with a start and end time.
  class Segment
    attr_reader :start_time, :end_time

    def initialize(start_time:, end_time:)
      raise ArgumentError, 'end_time must be after start_time' if end_time <= start_time

      @start_time = start_time
      @end_time = end_time
    end
  end
end
