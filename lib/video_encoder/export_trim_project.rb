# frozen_string_literal: true

module VideoEncoder
  # Selects project tracks and runs the complete trim export.
  class ExportTrimProject
    def initialize(selector:, exporter:)
      @selector = selector
      @exporter = exporter
    end

    def call(trim_project:, output_path:)
      sources = trim_project.segments.map(&:source).uniq

      exporter.call(
        trim_project: trim_project,
        video_tracks_by_source: selector.select_video_tracks(sources),
        audio_output_tracks: selector.select_audio_outputs(sources),
        subtitle_tracks_by_source:
          selector.select_subtitle_tracks(sources),
        output_path: output_path
      )
    end

    private

    attr_reader :selector, :exporter
  end
end
