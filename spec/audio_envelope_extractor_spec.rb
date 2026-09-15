# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::AudioEnvelopeExtractor do
  it 'extracts an RMS envelope from decoded audio samples' do
    samples = [
      1.0, -1.0,
      0.0, 0.0
    ].pack('e*')

    status = instance_double(
      Process::Status,
      success?: true
    )

    executor = class_double(Open3)

    allow(executor).to receive(:capture3)
      .and_return([samples, '', status])

    envelope = described_class.new(
      interval_seconds: 0.5,
      sample_rate: 4,
      executor: executor
    ).call(
      path: '/commun/source.m2t',
      stream_index: 1,
      start_seconds: 10.0,
      duration_seconds: 1.0
    )

    expect(envelope).to eq([1.0, 0.0])

    expect(executor).to have_received(:capture3).with(
      'ffmpeg',
      '-hide_banner',
      '-nostdin',
      '-loglevel', 'error',
      '-ss', '10.000000',
      '-i', '/commun/source.m2t',
      '-t', '1.000000',
      '-map', '0:1',
      '-vn',
      '-sn',
      '-dn',
      '-ac', '1',
      '-ar', '4',
      '-f', 'f32le',
      'pipe:1'
    )
  end

  it 'rejects an empty decoded signal' do
    status = instance_double(
      Process::Status,
      success?: true
    )

    executor = class_double(Open3)

    allow(executor).to receive(:capture3)
      .and_return([''.b, '', status])

    extractor = described_class.new(
      interval_seconds: 0.1,
      sample_rate: 1_000,
      executor: executor
    )

    expect do
      extractor.call(
        path: '/commun/source.m2t',
        stream_index: 1,
        start_seconds: 10.0,
        duration_seconds: 5.0
      )
    end.to raise_error(
      described_class::EnvelopeUnavailable,
      'audio envelope is unavailable'
    )
  end

  it 'preserves an ffmpeg failure diagnostic' do
    status = instance_double(
      Process::Status,
      success?: false,
      exitstatus: 1,
      termsig: nil,
      to_s: 'exit 1'
    )

    executor = class_double(Open3)

    allow(executor).to receive(:capture3)
      .and_return([''.b, 'decoder failed', status])

    extractor = described_class.new(
      interval_seconds: 0.1,
      sample_rate: 1_000,
      executor: executor
    )

    expect do
      extractor.call(
        path: '/commun/source.m2t',
        stream_index: 1,
        start_seconds: 10.0,
        duration_seconds: 5.0
      )
    end.to raise_error(
      VideoEncoder::CommandRunner::CommandFailed,
      a_string_including(
        'command failed: ffmpeg',
        'decoder failed'
      )
    )
  end
end
