# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::AudioOutputTrack do
  describe '#track_for' do
    it 'returns the selected track for a media source' do
      media = instance_double(VideoEncoder::Media)
      track = instance_double(VideoEncoder::Track)

      output_track = described_class.new(
        role: :french,
        tracks_by_source: {
          media => track
        }
      )

      expect(output_track.role).to eq(:french)
      expect(output_track.track_for(media)).to eq(track)
    end
  end

  describe '#complete_for?' do
    it 'is true when every media source has a selected track' do
      media_a = instance_double(VideoEncoder::Media)
      media_c = instance_double(VideoEncoder::Media)

      output_track = described_class.new(
        role: :french,
        tracks_by_source: {
          media_a => instance_double(VideoEncoder::Track),
          media_c => instance_double(VideoEncoder::Track)
        }
      )

      expect(output_track).to be_complete_for([media_a, media_c])
    end

    it 'is false when a media source has no selected track' do
      media_a = instance_double(VideoEncoder::Media)
      media_c = instance_double(VideoEncoder::Media)

      output_track = described_class.new(
        role: :original,
        tracks_by_source: {
          media_a => instance_double(VideoEncoder::Track)
        }
      )

      expect(output_track).not_to be_complete_for([media_a, media_c])
    end
  end

  describe '.new' do
    it 'rejects an unsupported audio role' do
      expect do
        described_class.new(
          role: :german,
          tracks_by_source: {}
        )
      end.to raise_error(
        ArgumentError,
        'unsupported audio role: german'
      )
    end
  end
end
