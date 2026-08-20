# frozen_string_literal: true

require 'pathname'

module VideoEncoder
  # Represents a media container with duration and associated tracks.
  class Media
    attr_reader :path,
                :duration,
                :video_tracks,
                :audio_tracks,
                :subtitle_tracks

    def initialize(
      path:,
      duration:,
      video_tracks: [],
      audio_tracks: [],
      subtitle_tracks: []
    )
      @path = Pathname.new(path)
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
