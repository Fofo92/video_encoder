# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleSynchronizationCorrection do
  it 'aligns the subtitle transport with the rendered video' do
    result = described_class.new.call(
      rendered_alignment: {
        offset_seconds: -2.12,
        confidence: 1.0
      },
      transport_alignment: {
        offset_seconds: -0.16,
        confidence: 0.98
      }
    )

    expect(result.fetch(:offset_seconds))
      .to be_within(0.000_001).of(-1.96)

    expect(result.fetch(:confidence))
      .to be_within(0.000_001).of(0.98)
  end

  it 'rejects an uncertain alignment' do
    correction = described_class.new(
      minimum_confidence: 0.95
    )

    expect do
      correction.call(
        rendered_alignment: {
          offset_seconds: -2.12,
          confidence: 0.99
        },
        transport_alignment: {
          offset_seconds: -0.16,
          confidence: 0.90
        }
      )
    end.to raise_error(
      described_class::AlignmentUnavailable,
      'subtitle alignment confidence is too low'
    )
  end
end
