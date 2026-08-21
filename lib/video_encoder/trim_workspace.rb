# frozen_string_literal: true

module VideoEncoder
  # Workspace for writing a trim project's MLT file.
  class TrimWorkspace
    def initialize(directory:)
      @directory = directory
    end

    def write_mlt(xml)
      File.write(mlt_path, xml)
    end

    def mlt_path
      File.join(directory, 'project.mlt')
    end

    def video_path
      File.join(directory, 'video.mkv')
    end

    def audio_path(output_track)
      File.join(directory, "audio_#{output_track.role}.mka")
    end

    private

    attr_reader :directory
  end
end
