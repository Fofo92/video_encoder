# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::AudioTimelineCorrelator do
  it 'detects content occurring earlier in the rendered timeline' do
    source = [
      0, 1, 4, 2, 8, 3, 6, 1, 5, 0,
      2, 7, 1, 3, 0, 0
    ]

    rendered = source.drop(2) + [0, 0]

    result = described_class.new(
      interval_seconds: 0.1,
      maximum_shift_seconds: 0.5
    ).call(
      source: source,
      rendered: rendered
    )

    expect(result.fetch(:offset_seconds))
      .to be_within(0.000_001).of(-0.2)

    expect(result.fetch(:confidence))
      .to be_within(0.000_001).of(1.0)
  end

  it 'detects aligned timelines' do
    source = [
      0, 1, 4, 2, 8, 3, 6, 1,
      5, 0, 2, 7, 1, 3, 0, 0
    ]

    result = described_class.new(
      interval_seconds: 0.1,
      maximum_shift_seconds: 0.5
    ).call(
      source: source,
      rendered: source.dup
    )

    expect(result.fetch(:offset_seconds))
      .to be_within(0.000_001).of(0.0)

    expect(result.fetch(:confidence))
      .to be_within(0.000_001).of(1.0)
  end

  it 'detects content occurring later in the rendered timeline' do
    source = [
      0, 1, 4, 2, 8, 3, 6, 1,
      5, 0, 2, 7, 1, 3, 0, 0
    ]

    rendered = [0, 0] + source.first(14)

    result = described_class.new(
      interval_seconds: 0.1,
      maximum_shift_seconds: 0.5
    ).call(
      source: source,
      rendered: rendered
    )

    expect(result.fetch(:offset_seconds))
      .to be_within(0.000_001).of(0.2)

    expect(result.fetch(:confidence))
      .to be_within(0.000_001).of(1.0)
  end

  it 'rejects constant signals' do
    correlator = described_class.new(
      interval_seconds: 0.1,
      maximum_shift_seconds: 0.5
    )

    expect do
      correlator.call(
        source: [1, 1, 1, 1],
        rendered: [1, 1, 1, 1]
      )
    end.to raise_error(
      described_class::CorrelationUnavailable,
      'audio correlation is unavailable'
    )
  end

  it 'rejects insufficient samples' do
    correlator = described_class.new(
      interval_seconds: 0.1,
      maximum_shift_seconds: 0.5
    )

    expect do
      correlator.call(
        source: [1],
        rendered: [1]
      )
    end.to raise_error(
      described_class::CorrelationUnavailable,
      'audio correlation is unavailable'
    )
  end
end
