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
        expect(config.directories.incoming).to eq('/commun/to_be_encoded')
        expect(config.directories.queue).to eq('/commun/Queue')
        expect(config.directories.encoded).to eq('/commun/Encoded')
        expect(config.directories.archive).to eq('/commun/Archive')
        expect(config.directories.encoding).to eq('/commun/Encoding')
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

        expect(config.ffmpeg.max_width).to eq(1280)
        expect(config.ffmpeg.max_height).to eq(720)
    end

  end
end
