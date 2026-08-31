# frozen_string_literal: true

module VideoEncoder
  # Plans and analyzes unconfirmed audio tracks for a trim project.
  class CheckTrimProjectAudio
    def initialize(selector:, planner:, checker:)
      @selector = selector
      @planner = planner
      @checker = checker
    end

    def call(trim_project:, confirmed_audio_tracks_by_source: {})
      sources = trim_project.segments.map(&:source).uniq

      samples = planner.call(
        trim_project: trim_project,
        video_tracks_by_source: selector.select_video_tracks(sources),
        audio_output_tracks: selector.select_audio_outputs(sources),
        subtitle_tracks_by_source: {},
        confirmed_audio_tracks_by_source: confirmed_audio_tracks_by_source
      )

      checker.call(samples)
    end

    private

    attr_reader :selector, :planner, :checker
  end
end
