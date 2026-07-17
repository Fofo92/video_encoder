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
end
