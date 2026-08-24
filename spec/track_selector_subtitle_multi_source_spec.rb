# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrackSelector do
  describe '#select_subtitle_tracks' do
    it 'omits subtitles when original audio is incomplete' do
      french_audio = instance_double(
        VideoEncoder::Track,
        language: 'fra',
        visual_impaired: false
      )

      original_audio = instance_double(
        VideoEncoder::Track,
        language: 'qaa',
        visual_impaired: false
      )

      subtitle = instance_double(
        VideoEncoder::Track,
        language: 'fra',
        hearing_impaired: false
      )

      media_with_original = instance_double(
        VideoEncoder::Media,
        audio_tracks: [french_audio, original_audio],
        subtitle_tracks: [subtitle]
      )

      media_without_original = instance_double(
        VideoEncoder::Media,
        audio_tracks: [french_audio],
        subtitle_tracks: []
      )

      selection = described_class.new.select_subtitle_tracks(
        [media_with_original, media_without_original]
      )

      expect(selection).to eq({})
    end
  end
end
