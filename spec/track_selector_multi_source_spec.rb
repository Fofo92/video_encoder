# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrackSelector do
  subject(:selector) { described_class.new }

  describe '#select_audio_outputs' do
    it 'omits the original output when a source has no qaa track' do
      french_a = instance_double(
        VideoEncoder::Track,
        language: 'fra',
        visual_impaired: false
      )

      original_a = instance_double(
        VideoEncoder::Track,
        language: 'qaa',
        visual_impaired: false
      )

      french_c = instance_double(
        VideoEncoder::Track,
        language: 'fra',
        visual_impaired: false
      )

      media_a = instance_double(
        VideoEncoder::Media,
        audio_tracks: [french_a, original_a]
      )

      media_c = instance_double(
        VideoEncoder::Media,
        audio_tracks: [french_c]
      )

      outputs = selector.select_audio_outputs([media_a, media_c])

      expect(outputs.map(&:role)).to eq([:french])
      expect(outputs.first.track_for(media_a)).to eq(french_a)
      expect(outputs.first.track_for(media_c)).to eq(french_c)
    end

    it 'builds French and original outputs from their recognized roles' do
      french_a = instance_double(
        VideoEncoder::Track,
        language: 'fra',
        visual_impaired: false
      )

      original_a = instance_double(
        VideoEncoder::Track,
        language: 'qaa',
        visual_impaired: false
      )

      french_c = instance_double(
        VideoEncoder::Track,
        language: 'fra',
        visual_impaired: false
      )

      original_c = instance_double(
        VideoEncoder::Track,
        language: 'qaa',
        visual_impaired: false
      )

      german_c = instance_double(
        VideoEncoder::Track,
        language: 'deu',
        visual_impaired: false
      )

      media_a = instance_double(
        VideoEncoder::Media,
        audio_tracks: [french_a, original_a]
      )

      media_c = instance_double(
        VideoEncoder::Media,
        audio_tracks: [french_c, original_c, german_c]
      )

      outputs = selector.select_audio_outputs([media_a, media_c])

      expect(outputs.map(&:role)).to eq(%i[french original])

      original = outputs.last

      expect(original.track_for(media_a)).to eq(original_a)
      expect(original.track_for(media_c)).to eq(original_c)
    end
  end
end
