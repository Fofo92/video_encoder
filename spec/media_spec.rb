# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Media do
  it 'stores duration' do
    media = described_class.new(duration: 123.4)

    expect(media.duration).to eq(123.4)
  end
end
