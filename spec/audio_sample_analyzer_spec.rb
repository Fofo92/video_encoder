# frozen_string_literal: true

require 'spec_helper'
require 'open3'

RSpec.describe VideoEncoder::AudioSampleAnalyzer do
  let(:executor) { class_double(Open3) }

  let(:source) do
    instance_double(
      VideoEncoder::Media,
      path: Pathname('/media/movie.m2t')
    )
  end

  let(:track) do
    VideoEncoder::Track.new(
      index: 2,
      type: :audio,
      language: 'qaa'
    )
  end

  let(:sample) do
    {
      source: source,
      track: track,
      start_frame: 750,
      end_frame: 2249,
      frame_rate: Rational(25, 1)
    }
  end

  it 'reports decoded audio with a significant signal level' do
    status = instance_double(Process::Status, success?: true)

    diagnostic = <<~LOG
      [Parsed_volumedetect_0 @ diagnostic] n_samples: 5760000
      [Parsed_volumedetect_0 @ diagnostic] mean_volume: -24.0 dB
      [Parsed_volumedetect_0 @ diagnostic] max_volume: -8.0 dB
    LOG

    allow(executor).to receive(:capture3)
      .and_return(['', diagnostic, status])

    analyzer = described_class.new(
      executor: executor,
      signal_threshold_db: -60
    )

    result = analyzer.call(sample)

    expect(result).to eq(
      status: :signal_detected,
      sample_count: 5_760_000,
      mean_volume_db: -24.0,
      max_volume_db: -8.0
    )
  end

  it 'analyzes only the selected track and inclusive frame interval' do
    status = instance_double(Process::Status, success?: true)

    diagnostic = <<~LOG
      [Parsed_volumedetect_0 @ diagnostic] n_samples: 5760000
      [Parsed_volumedetect_0 @ diagnostic] mean_volume: -24.0 dB
      [Parsed_volumedetect_0 @ diagnostic] max_volume: -8.0 dB
    LOG

    allow(executor).to receive(:capture3)
      .and_return(['', diagnostic, status])

    described_class.new(executor: executor).call(sample)

    expect(executor).to have_received(:capture3).with(
      'ffmpeg',
      '-hide_banner',
      '-nostdin',
      '-nostats',
      '-loglevel', 'info',
      '-xerror',
      '-ss', '30.000000000',
      '-i', '/media/movie.m2t',
      '-t', '60.000000000',
      '-map', '0:2',
      '-vn',
      '-sn',
      '-dn',
      '-af', 'volumedetect',
      '-f', 'null',
      '-'
    )
  end

  it 'reports a very low audio level as inconclusive' do
    status = instance_double(Process::Status, success?: true)

    diagnostic = <<~LOG
      [Parsed_volumedetect_0 @ diagnostic] n_samples: 5760000
      [Parsed_volumedetect_0 @ diagnostic] mean_volume: -85.0 dB
      [Parsed_volumedetect_0 @ diagnostic] max_volume: -75.0 dB
    LOG

    allow(executor).to receive(:capture3)
      .and_return(['', diagnostic, status])

    result = described_class.new(
      executor: executor,
      signal_threshold_db: -60
    ).call(sample)

    expect(result).to eq(
      status: :inconclusive,
      sample_count: 5_760_000,
      mean_volume_db: -85.0,
      max_volume_db: -75.0
    )
  end

  it 'reports no decoded samples as inconclusive' do
    status = instance_double(Process::Status, success?: true)

    allow(executor).to receive(:capture3)
      .and_return(
        [
          '',
          '[Parsed_volumedetect_0 @ diagnostic] n_samples: 0',
          status
        ]
      )

    result = described_class.new(executor: executor).call(sample)

    expect(result).to eq(
      status: :inconclusive,
      sample_count: 0,
      mean_volume_db: nil,
      max_volume_db: nil
    )
  end

  it 'preserves a command failure even when volume measurements exist' do
    status = instance_double(
      Process::Status,
      success?: false,
      exitstatus: 1,
      termsig: nil,
      to_s: 'exit 1'
    )

    diagnostic = <<~LOG
      [Parsed_volumedetect_0 @ diagnostic] n_samples: 48000
      [Parsed_volumedetect_0 @ diagnostic] mean_volume: -24.0 dB
      [Parsed_volumedetect_0 @ diagnostic] max_volume: -8.0 dB
      Error while decoding audio
    LOG

    allow(executor).to receive(:capture3)
      .and_return(['', diagnostic, status])

    expect do
      described_class.new(executor: executor).call(sample)
    end.to raise_error(
      VideoEncoder::CommandRunner::CommandFailed
    ) { |error|
      expect(error.exit_status).to eq(1)
      expect(error.term_signal).to be_nil
      expect(error.message).to include('Error while decoding audio')
    }
  end
end
