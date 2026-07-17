# frozen_string_literal: true

module VideoEncoder
  # Represents a media track, such as audio or subtitles.
  class Track
    attr_reader :index,
                :type,
                :language,
                :codec,
                :default,
                :forced

    def initialize(
      index:,
      type:,
      language: nil,
      codec: nil,
      default: false,
      forced: false
    )
      @index = index
      @type = type
      @language = language
      @codec = codec
      @default = default
      @forced = forced
    end
  end
end
