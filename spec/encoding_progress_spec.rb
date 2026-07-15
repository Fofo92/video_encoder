# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::EncodingProgress do
  subject(:progress) { described_class.new(100.0) }

  describe '#percent' do
    it 'returns 0 at the beginning' do
      expect(progress.percent(0)).to eq(0)
    end

    it 'returns 50 halfway' do
      expect(progress.percent(50)).to eq(50)
    end

    it 'returns 100 at the end' do
      expect(progress.percent(100)).to eq(100)
    end

    it 'never exceeds 100' do
      expect(progress.percent(150)).to eq(100)
    end

    it 'never goes below 0' do
      expect(progress.percent(-10)).to eq(0)
    end
  end
end
