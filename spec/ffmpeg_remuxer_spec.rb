# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::FfmpegRemuxer do
  subject(:remuxer) { described_class.new(runner: runner) }

  let(:runner) { instance_double('CommandRunner') }

  let(:french_audio) do
    instance_double(
      VideoEncoder::AudioOutputTrack,
      role: :french
    )
  end

  let(:original_audio) do
    instance_double(
      VideoEncoder::AudioOutputTrack,
      role: :original
    )
  end

  describe '#remux' do
    it 'combines video and audio while preserving the audio roles' do
      allow(runner).to receive(:run)

      remuxer.remux(
        video_path: 'tmp/video.mkv',
        audio_inputs: [
          {
            path: 'tmp/audio_french.mka',
            output_track: french_audio
          },
          {
            path: 'tmp/audio_original.mka',
            output_track: original_audio
          }
        ],
        output_path: 'tmp/movie.mkv'
      )

      expect(runner).to have_received(:run).with(
        'ffmpeg',
        '-i', 'tmp/video.mkv',
        '-i', 'tmp/audio_french.mka',
        '-i', 'tmp/audio_original.mka',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-map', '2:a:0',
        '-c', 'copy',
        '-metadata:s:a:0', 'language=fra',
        '-metadata:s:a:1', 'language=qaa',
        'tmp/movie.mkv'
      )
    end
  end
end
