# frozen_string_literal: true

module VideoEncoder
  # Represents a media track, such as audio or subtitles.
  class Track
    attr_reader :index,
                :type,
                :language,
                :codec,
                :default,
                :forced,
                :hearing_impaired,
                :visual_impaired

    def initialize(
      index:,
      type:,
      language: nil,
      codec: nil,
      default: false,
      forced: false,
      hearing_impaired: false,
      visual_impaired: false
    )
      @index = index
      @type = type
      @language = language
      @codec = codec
      @default = default
      @forced = forced
      @hearing_impaired = hearing_impaired
      @visual_impaired = visual_impaired
    end
  end
end
