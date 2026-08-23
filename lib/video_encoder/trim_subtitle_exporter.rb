# frozen_string_literal: true

module VideoEncoder
  # Produces one composed SRT track for a trim project.
  class TrimSubtitleExporter
    def initialize(processor:, composer:, workspace:)
      @processor = processor
      @composer = composer
      @workspace = workspace
    end

    def call(
      trim_project:,
      video_tracks_by_source:,
      subtitle_tracks_by_source:
    )
      timeline_start = 0
      normalized_segments = []

      trim_project.segments.each_with_index do |segment, index|
        video_track = video_tracks_by_source.fetch(segment.source)
        duration = segment_duration(segment, video_track)
        subtitle_track = subtitle_tracks_by_source[segment.source]

        if subtitle_track
          normalized_segments << processor.call(
            segment: segment,
            video_track: video_track,
            subtitle_track: subtitle_track,
            timeline_start: timeline_start,
            transport_path: workspace.subtitle_transport_path(index),
            srt_path: workspace.subtitle_srt_path(index)
          )
        end

        timeline_start += duration
      end

      composed = composer.call(normalized_segments)

      return if composed.empty?

      workspace.write_subtitles(composed)
      workspace.subtitle_path
    end

    private

    attr_reader :processor, :composer, :workspace

    def segment_duration(segment, video_track)
      frame_count = segment.end_frame - segment.start_frame + 1

      Rational(frame_count, 1) / video_track.frame_rate
    end
  end
end
