# frozen_string_literal: true

module VideoEncoder
  class TrackSelector
    FRENCH_CODES = %w[fra fre].freeze
    ORIGINAL_VERSION_CODES = %w[qaa].freeze

    def select(media)
      {
        video: media.video_tracks.first,
        audio: select_audio(media.audio_tracks),
        subtitles: select_subtitles(media)
      }
    end

    def select_audio_outputs(media_sources)
      french = build_audio_output(media_sources, :french) do |track|
        french?(track)
      end

      original = build_audio_output(media_sources, :original) do |track|
        original_version?(track)
      end

      [french, original].compact
    end

    private

    def special_audio?(track)
      SPECIAL_AUDIO_CODES.include?(track.language)
    end

    def select_audio(tracks)
      usable = tracks.reject(&:visual_impaired)

      french = usable.find { |track| french?(track) }
      original = usable.find { |track| original_version?(track) }

      [french, original].compact.uniq
    end

    def select_subtitles(media)
      original_audio = select_audio(media.audio_tracks).find { |track| !french?(track) }

      return [] unless original_audio

      media.subtitle_tracks.select do |track|
        french?(track) && !track.hearing_impaired
      end
    end

    def french?(track)
      FRENCH_CODES.include?(track.language)
    end

    def original_version?(track)
      ORIGINAL_VERSION_CODES.include?(track.language)
    end

    def build_audio_output(media_sources, role, &predicate)
      tracks = media_sources.map do |media|
        usable = media.audio_tracks.reject(&:visual_impaired)

        usable.find(&predicate)
      end

      return unless tracks.all?

      AudioOutputTrack.new(
        role: role,
        tracks_by_source: media_sources.zip(tracks).to_h
      )
    end
  end
end
