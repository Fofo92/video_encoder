# frozen_string_literal: true

module VideoEncoder
  # Represents a video segment with a start and end time.
  class Segment
    attr_reader :start_time, :end_time, :start_frame, :end_frame

    def initialize(start_time: nil, end_time: nil, start_frame: nil, end_frame: nil)
      @start_time = start_time
      @end_time = end_time
      @start_frame = start_frame
      @end_frame = end_frame

      validate_boundaries
    end

    def duration
      return unless start_time && end_time

      time_in_milliseconds(end_time) - time_in_milliseconds(start_time)
    end

    def ==(other)
      other.is_a?(self.class) &&
        start_time == other.start_time &&
        end_time == other.end_time &&
        start_frame == other.start_frame &&
        end_frame == other.end_frame
    end

    def frame_count
      end_frame - start_frame + 1
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

    def validate_boundaries
      if start_time && end_time
        raise ArgumentError, 'end_time must be after start_time' if end_time <= start_time
      elsif start_frame && end_frame
        raise ArgumentError, 'end_frame must be after start_frame' if end_frame <= start_frame
      else
        raise ArgumentError, 'segment boundaries are incomplete'
      end
    end
  end
end
