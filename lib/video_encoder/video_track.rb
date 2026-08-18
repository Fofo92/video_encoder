# frozen_string_literal: true

module VideoEncoder
  # Represents a video track with its specific properties.
  class VideoTrack < Track
    attr_reader :frame_rate

    def initialize(frame_rate:, **attributes)
      super(**attributes)
      @frame_rate = frame_rate
    end
  end
end
