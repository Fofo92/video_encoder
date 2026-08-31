# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::AudioPreflightChecker do
  it 'keeps an inconclusive audio result associated with its source and track' do
    source = instance_double(VideoEncoder::Media)
    audio = VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra'
    )
    subtitle = VideoEncoder::Track.new(
      index: 2,
      type: :subtitle,
      language: 'fra'
    )

    audio_sample = {
      source: source,
      track: audio,
      start_frame: 750,
      end_frame: 2249,
      frame_rate: Rational(25, 1)
    }
    subtitle_sample = audio_sample.merge(track: subtitle)

    analysis = {
      status: :inconclusive,
      sample_count: 0,
      mean_volume_db: nil,
      max_volume_db: nil
    }

    analyzer = instance_double(VideoEncoder::AudioSampleAnalyzer)
    allow(analyzer).to receive(:call)
      .with(audio_sample)
      .and_return(analysis)

    results = described_class.new(analyzer: analyzer).call(
      [audio_sample, subtitle_sample]
    )

    expect(results).to eq(
      [audio_sample.merge(analysis: analysis)]
    )
    expect(analyzer).to have_received(:call)
      .with(audio_sample).once
  end

  it 'propagates an invalid audio measurement' do
    audio = VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra'
    )
    sample = { track: audio }

    analyzer = instance_double(VideoEncoder::AudioSampleAnalyzer)
    allow(analyzer).to receive(:call)
      .with(sample)
      .and_raise(
        VideoEncoder::AudioSampleAnalyzer::InvalidMeasurement,
        'missing decoded sample count'
      )

    checker = described_class.new(analyzer: analyzer)

    expect { checker.call([sample]) }.to raise_error(
      VideoEncoder::AudioSampleAnalyzer::InvalidMeasurement,
      'missing decoded sample count'
    )
  end
end
