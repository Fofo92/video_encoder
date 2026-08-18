# frozen_string_literal: true

module VideoEncoder
  # Represents a deliberate blank interval in a trim project.
  class Gap
    attr_reader :frame_count

    def initialize(frame_count:)
      raise ArgumentError, 'frame_count must be positive' unless frame_count.positive?

      @frame_count = frame_count
    end

    def ==(other)
      other.is_a?(self.class) &&
        frame_count == other.frame_count
    end
  end
end
