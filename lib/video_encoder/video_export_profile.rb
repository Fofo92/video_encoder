# frozen_string_literal: true

module VideoEncoder
  # Video export profile configuration class
  class VideoExportProfile
    attr_reader :width,
                :height,
                :frame_rate,
                :colorspace,
                :display_aspect_ratio,
                :sample_aspect_ratio

    def self.hd_720p25
      new(
        width: 1280,
        height: 720,
        frame_rate: Rational(25, 1),
        progressive: true,
        colorspace: 709,
        display_aspect_ratio: Rational(16, 9),
        sample_aspect_ratio: Rational(1, 1)
      )
    end

    def initialize(
      width:,
      height:,
      frame_rate:,
      progressive:,
      colorspace:,
      display_aspect_ratio:,
      sample_aspect_ratio:
    )
      @width = width
      @height = height
      @frame_rate = frame_rate
      @progressive = progressive
      @colorspace = colorspace
      @display_aspect_ratio = display_aspect_ratio
      @sample_aspect_ratio = sample_aspect_ratio
    end

    def progressive?
      @progressive
    end
  end
end
