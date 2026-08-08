# frozen_string_literal: true

module VideoEncoder
  # Coordinates the construction of a trim project from a media.
  class TrimEditor
    attr_reader :media, :current_frame, :in_frame, :out_frame

    def initialize(media:)
      @media = media
      @current_frame = 0
    end

    def mark_in
      @in_frame = current_frame
    end

    def mark_out
      @out_frame = current_frame
    end

    def seek_to(frame)
      @current_frame = frame
    end
  end
end
