# frozen_string_literal: true

require 'time'

module VideoEncoder
  # Serializes the dated technical inspection of a media source.
  class MediaInspectionSerializer
    def call(media)
      inspection = {
        duration: media.duration
      }

      add_observation(inspection, media)

      return inspection if media.tracks.empty?

      inspection.merge(
        video_tracks: media.video_tracks.map do |track|
          serialize_video_track(track)
        end,
        audio_tracks: media.audio_tracks.map do |track|
          serialize_audio_track(track)
        end,
        subtitle_tracks: media.subtitle_tracks.map do |track|
          serialize_subtitle_track(track)
        end
      )
    end

    private

    def add_observation(inspection, media)
      inspection[:inspected_at] = media.inspected_at.iso8601 if media.inspected_at

      return unless media.size_bytes

      inspection[:size_bytes] = media.size_bytes
    end

    def serialize_video_track(track)
      {
        index: track.index,
        codec: track.codec,
        width: track.width,
        height: track.height,
        frame_rate: serialize_frame_rate(
          track.frame_rate
        )
      }
    end

    def serialize_audio_track(track)
      {
        index: track.index,
        codec: track.codec,
        language: track.language,
        default: track.default,
        visual_impaired: track.visual_impaired
      }
    end

    def serialize_subtitle_track(track)
      {
        index: track.index,
        codec: track.codec,
        language: track.language,
        default: track.default,
        forced: track.forced,
        hearing_impaired: track.hearing_impaired
      }
    end

    def serialize_frame_rate(frame_rate)
      return unless frame_rate

      {
        numerator: frame_rate.numerator,
        denominator: frame_rate.denominator
      }
    end
  end
end
