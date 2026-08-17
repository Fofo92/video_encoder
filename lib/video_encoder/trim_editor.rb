# frozen_string_literal: true

module VideoEncoder
  # Coordinates the construction of a trim project from a media.
  class TrimEditor
    attr_reader :media, :project, :current_frame, :in_frame, :out_frame

    def initialize(media:, project:)
      @media = media
      @project = project
      @current_frame = 0
    end

    def validate_selection
      project.add_segment(
        Segment.new(
          start_frame: in_frame,
          end_frame: out_frame
        )
      )
      @in_frame = nil
      @out_frame = nil
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
