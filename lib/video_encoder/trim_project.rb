module VideoEncoder
  # Represents a set of trim segments for a video project.
  class TrimProject
    attr_reader :source, :segments, :timeline

    def initialize(source:)
      @source = source
      @segments = []
      @timeline = []
    end

    def add_segment(segment)
      previous = segments.last

      if previous && segments_overlap_or_are_contiguous?(previous, segment)
        raise ArgumentError, 'segments must not overlap or be contiguous'
      end

      @segments << segment
      @timeline << segment
    end

    def duration
      segments.sum(&:duration)
    end

    def remove_segment(segment)
      @segments.delete(segment)
    end

    def add_gap(gap)
      timeline << gap
    end

    private

    def segments_overlap_or_are_contiguous?(previous, segment)
      return false if previous.source != segment.source

      if previous.end_frame && segment.start_frame
        segment.start_frame <= previous.end_frame + 1
      else
        segment.start_time <= previous.end_time
      end
    end
  end
end
