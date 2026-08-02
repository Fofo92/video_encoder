module VideoEncoder
  # Represents a set of trim segments for a video project.
  class TrimProject
    attr_reader :source, :segments

    def initialize(source:)
      @source = source
      @segments = []
    end

    def add_segment(segment)
      @segments << segment
    end
  end
end
