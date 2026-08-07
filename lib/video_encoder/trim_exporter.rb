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

    def call(trim_project:, tracks:, output_path:)
      xml = builder.build(trim_project)

      workspace.write_mlt(xml)

      renderer.render_video(
        project_path: workspace.mlt_path,
        output_path: workspace.video_path
      )

      audio_inputs = tracks.map do |track|
        audio_path = workspace.audio_path(track)

        renderer.render_audio(
          project_path: workspace.mlt_path,
          output_path: audio_path
        )

        {
          path: audio_path,
          track: track
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
