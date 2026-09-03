# frozen_string_literal: true

module VideoEncoder
  # Represents a video track with its specific properties.
  class VideoTrack < Track
    attr_reader :frame_rate, :width, :height

    def initialize(
      frame_rate:,
      width: nil,
      height: nil,
      **attributes
    )
      super(**attributes)
      @frame_rate = frame_rate
      @width = width
      @height = height
    end
  end
end
