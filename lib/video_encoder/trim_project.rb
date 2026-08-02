module VideoEncoder
  # Represents a set of trim segments for a video project.
  class TrimProject
    attr_reader :source, :segments

    def initialize(source:)
      @source = source
      @segments = []
    end

    def add_segment(segment)
      previous = segments.last

      if previous && (segment.start_time <= previous.end_time)
        raise ArgumentError, 'segments must not overlap or be contiguous'
      end

      @segments << segment
    end

    def duration
      segments.sum(&:duration)
    end
  end
end
