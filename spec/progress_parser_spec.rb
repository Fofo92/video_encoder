# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ProgressParser do
  subject(:parser) { described_class.new }

  describe '#parse' do
    it 'parses out_time_ms' do
      expect(
        parser.parse('out_time_ms=12500000')
      ).to eq(12.5)
    end

    it 'returns nil for unrelated lines' do
      expect(
        parser.parse('frame=123')
      ).to be_nil
    end

    it 'returns nil for empty lines' do
      expect(
        parser.parse('')
      ).to be_nil
    end

    it 'returns 0 for the beginning of the encoding' do
      expect(
        parser.parse('out_time_ms=0')
      ).to eq(0.0)
    end
  end
end
