# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::VideoTimelineCorrelator do
  it 'detects frames occurring earlier in the rendered timeline' do
    source = [
      [0, 1, 4, 2],
      [8, 3, 6, 1],
      [5, 0, 2, 7],
      [1, 3, 0, 9],
      [6, 2, 8, 4],
      [3, 7, 1, 5],
      [9, 4, 0, 2],
      [2, 6, 3, 8]
    ]

    rendered = source.drop(2) + [
      [0, 0, 0, 0],
      [0, 0, 0, 0]
    ]

    result = described_class.new(
      frame_rate: 10,
      maximum_shift_seconds: 0.2
    ).call(
      source: source,
      rendered: rendered
    )

    expect(result.fetch(:offset_seconds))
      .to be_within(0.000_001).of(-0.2)

    expect(result.fetch(:confidence))
      .to be_within(0.000_001).of(1.0)
  end
end
