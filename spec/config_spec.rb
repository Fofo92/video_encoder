# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Config do
  describe '.load' do
    subject(:config) { described_class.load }

    it 'loads the database path' do
      expect(config.database)
        .to eq('video_encoder.db')
    end

    it 'loads the encoder name' do
      expect(config.encoder)
        .to eq('ffmpeg')
    end

    it 'loads directories' do
      expect(config.directories.incoming)
        .to eq('to_be_encoded')

      expect(config.directories.queue)
        .to eq('queue')

      expect(config.directories.encoded)
        .to eq('encoded')

      expect(config.directories.archive)
        .to eq('archive')
    end

    it 'loads ffmpeg options' do
      expect(config.ffmpeg.video_codec)
        .to eq('hevc_nvenc')

      expect(config.ffmpeg.audio_codec)
        .to eq('aac')

      expect(config.ffmpeg.preset)
        .to eq('p6')

      expect(config.ffmpeg.cq)
        .to eq(22)
    end
  end
end
