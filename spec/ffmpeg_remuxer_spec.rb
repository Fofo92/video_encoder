# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::FfmpegRemuxer do
  subject(:remuxer) { described_class.new(runner: runner) }

  let(:runner) { instance_double('CommandRunner') }

  let(:french_audio) do
    VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra',
      codec: 'eac3'
    )
  end

  describe '#remux' do
    it 'combines video and audio while preserving the audio language' do
      allow(runner).to receive(:run)

      remuxer.remux(
        video_path: 'tmp/video.mkv',
        audio_inputs: [
          {
            path: 'tmp/audio_fra.mka',
            track: french_audio
          }
        ],
        output_path: 'tmp/movie.mkv'
      )

      expect(runner).to have_received(:run).with(
        'ffmpeg',
        '-i', 'tmp/video.mkv',
        '-i', 'tmp/audio_fra.mka',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-c', 'copy',
        '-metadata:s:a:0', 'language=fra',
        'tmp/movie.mkv'
      )
    end
  end
end
