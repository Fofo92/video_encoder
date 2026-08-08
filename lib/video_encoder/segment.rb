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

    def duration
      time_in_milliseconds(end_time) -
        time_in_milliseconds(start_time)
    end

    def ==(other)
      other.is_a?(self.class) &&
        start_time == other.start_time &&
        end_time == other.end_time
    end

    private

    def time_in_milliseconds(time)
      hours, minutes, seconds = time.split(':')

      (
        hours.to_i * 3_600_000 +
        minutes.to_i * 60_000 +
        seconds.to_f * 1_000
      ).round
    end
  end
end
