# frozen_string_literal: true

module VideoEncoder
  # Plans and analyzes unconfirmed audio tracks for a trim project.
  class CheckTrimProjectAudio
    def initialize(selector:, planner:, checker:, include_selection: false)
      @selector = selector
      @planner = planner
      @checker = checker
      @include_selection = include_selection
    end

    def call(trim_project:, confirmed_audio_tracks_by_source: {})
      sources = trim_project.segments.map(&:source).uniq
      selection = trim_project.track_selection if trim_project.respond_to?(:track_selection)
      selector = TrackSelector.for_mode(selection&.fetch('mode', nil), fallback: @selector)

      samples = planner.call(
        trim_project: trim_project,
        video_tracks_by_source: selector.select_video_tracks(sources),
        audio_output_tracks: selector.select_audio_outputs(sources),
        subtitle_tracks_by_source: {},
        confirmed_audio_tracks_by_source: confirmed_audio_tracks_by_source
      )

      results = checker.call(samples)
      return results unless @include_selection

      { audio_checks: results, mode: selection&.fetch('mode', nil),
        subtitle_selection: subtitle_selection(selector, sources) }
    end

    private

    attr_reader :selector, :planner, :checker

    def subtitle_selection(selector, sources)
      tracks = selector.select_subtitle_tracks(sources)
      sources.map do |source|
        track = tracks[source]
        { source: source.path.to_s, track_index: track&.index, language: track&.language }
      end
    end
  end
end
