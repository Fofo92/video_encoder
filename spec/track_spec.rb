# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Track do
  it 'stores metadata' do
    track = described_class.new(
      index: 1,
      type: :audio,
      language: "fra",
      codec: "aac"
    )

    expect(track.language).to eq("fra")
  end

  # describe '#frame_rate' do
  #   it 'returns the frame rate' do
  #     track = described_class.new(
  #       index: 0,
  #       type: :video,
  #       frame_rate: Rational(25, 1)
  #     )

  #     expect(track.frame_rate).to eq(Rational(25, 1))
  #   end
  # end
end
