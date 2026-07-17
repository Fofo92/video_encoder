# frozen_string_literal: true

module VideoEncoder
  # Represents a media container with duration and associated tracks.
  class Media
    attr_reader :duration,
                :video_tracks,
                :audio_tracks,
                :subtitle_tracks

    def initialize(
      duration:,
      video_tracks: [],
      audio_tracks: [],
      subtitle_tracks: []
    )
      @duration = duration
      @video_tracks = video_tracks
      @audio_tracks = audio_tracks
      @subtitle_tracks = subtitle_tracks
    end

    def tracks
      video_tracks + audio_tracks + subtitle_tracks
    end
  end
end
