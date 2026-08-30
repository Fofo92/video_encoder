# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::FfmpegRemuxer, 'output safety' do
  it 'disables interactive input and refuses to overwrite the output' do
    runner = instance_double(VideoEncoder::CommandRunner)
    remuxer = described_class.new(runner: runner)

    allow(runner).to receive(:run)

    remuxer.remux(
      video_path: '/tmp/video.mkv',
      audio_inputs: [],
      output_path: '/tmp/movie.mkv'
    )

    expect(runner).to have_received(:run).with(
      'ffmpeg',
      '-nostdin',
      '-n',
      '-i', '/tmp/video.mkv',
      '-map', '0:v:0',
      '-c', 'copy',
      '/tmp/movie.mkv'
    )
  end
end
