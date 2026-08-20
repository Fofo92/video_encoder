# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Media do
  it 'stores its file path' do
    media = described_class.new(
      path: 'movie.mkv',
      duration: 123.4
    )

    expect(media.path).to eq(Pathname('movie.mkv'))
  end

  it 'stores duration' do
    media = described_class.new(
      path: 'movie.mkv',
      duration: 123.4
    )

    expect(media.duration).to eq(123.4)
  end
end
