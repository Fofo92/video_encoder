# frozen_string_literal: true

module VideoEncoder
  # Orchestrates the production of a trimmed media file.
  class TrimExporter
    def initialize(builder:, renderer:, remuxer:, workspace:)
      @builder = builder
      @renderer = renderer
      @remuxer = remuxer
      @workspace = workspace
    end

    def call(
      trim_project:,
      video_tracks_by_source:,
      audio_output_tracks:,
      output_path:
    )
      sources = trim_project.segments.map(&:source).uniq

      video_xml = builder.build(
        trim_project,
        audio_index: -1,
        video_tracks_by_source: video_tracks_by_source
      )

      workspace.write_mlt(video_xml)

      renderer.render_video(
        project_path: workspace.mlt_path,
        output_path: workspace.video_path
      )

      audio_inputs = audio_output_tracks
                     .select { |output_track| output_track.complete_for?(sources) }
                     .map do |output_track|
        tracks_by_source = sources.to_h do |source|
          [source, output_track.track_for(source)]
        end

        audio_xml = builder.build(
          trim_project,
          video_index: -1,
          audio_tracks_by_source: tracks_by_source,
          video_tracks_by_source: video_tracks_by_source
        )

        workspace.write_mlt(audio_xml)

        audio_path = workspace.audio_path(output_track)

        renderer.render_audio(
          project_path: workspace.mlt_path,
          output_path: audio_path
        )

        {
          path: audio_path,
          output_track: output_track
        }
      end

      remuxer.remux(
        video_path: workspace.video_path,
        audio_inputs: audio_inputs,
        output_path: output_path
      )
    end

    private

    attr_reader :builder, :renderer, :remuxer, :workspace
  end
end
