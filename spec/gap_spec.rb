# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Gap do
  describe '#frame_count' do
    it 'returns the number of frames occupied by the gap' do
      gap = described_class.new(frame_count: 50)

      expect(gap.frame_count).to eq(50)
    end
  end

  describe '#initialize' do
    it 'rejects a gap with no frames' do
      expect do
        described_class.new(frame_count: 0)
      end.to raise_error(ArgumentError)
    end

    it 'rejects a gap with a negative frame count' do
      expect do
        described_class.new(frame_count: -1)
      end.to raise_error(ArgumentError)
    end
  end
  describe '#==' do
    it 'is equal to another gap with the same frame count' do
      first = described_class.new(frame_count: 50)
      second = described_class.new(frame_count: 50)

      expect(first).to eq(second)
    end
  end
end
