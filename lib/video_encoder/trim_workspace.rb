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

    def subtitle_transport_path(segment_index)
      File.join(
        directory,
        "subtitle_segment_#{segment_index}.ts"
      )
    end

    def subtitle_manifest_path(run_index)
      File.join(
        directory,
        "subtitle_project_#{run_index}.ffconcat"
      )
    end

    def subtitle_project_transport_path(run_index)
      File.join(
        directory,
        "subtitle_project_#{run_index}.ts"
      )
    end

    def subtitle_project_srt_path(run_index)
      File.join(
        directory,
        "subtitle_project_#{run_index}.srt"
      )
    end

    def subtitle_path
      File.join(directory, 'subtitles.srt')
    end

    def write_subtitles(srt)
      File.write(subtitle_path, srt)
    end

    private

    attr_reader :directory
  end
end
