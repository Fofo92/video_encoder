# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::VideoFrameSequenceExtractor do
  it 'extracts normalized grayscale video frames' do
    frames = [
      0, 1, 2, 3,
      4, 5, 6, 7
    ].pack('C*')

    status = instance_double(
      Process::Status,
      success?: true
    )

    executor = class_double(Open3)

    allow(executor).to receive(:capture3)
      .and_return([frames, '', status])

    result = described_class.new(
      width: 2,
      height: 2,
      frame_rate: 25,
      seek_preroll_seconds: 2.0,
      executor: executor
    ).call(
      path: '/commun/source.m2t',
      stream_index: 0,
      start_seconds: 10.0,
      duration_seconds: 1.0
    )

    expect(result).to eq(
      [
        [0, 1, 2, 3],
        [4, 5, 6, 7]
      ]
    )

    expect(executor).to have_received(:capture3).with(
      'ffmpeg',
      '-hide_banner',
      '-nostdin',
      '-loglevel', 'error',
      '-ss', '8.000000',
      '-i', '/commun/source.m2t',
      '-ss', '2.000000',
      '-t', '1.000000',
      '-map', '0:0',
      '-an',
      '-sn',
      '-dn',
      '-vf', 'scale=2:2,format=gray,fps=25',
      '-f', 'rawvideo',
      'pipe:1'
    )
  end
end
