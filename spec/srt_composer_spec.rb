# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SrtComposer do
  describe '#call' do
    it 'renumbers subtitle entries across segments' do
      first_segment = <<~SRT
        1
        00:00:01,000 --> 00:00:02,000
        Premier segment.

      SRT

      second_segment = <<~SRT
        1
        00:01:01,000 --> 00:01:02,000
        Deuxième segment.

      SRT

      composed = described_class.new.call(
        [first_segment, second_segment]
      )

      expect(composed).to eq(<<~SRT)
        1
        00:00:01,000 --> 00:00:02,000
        Premier segment.

        2
        00:01:01,000 --> 00:01:02,000
        Deuxième segment.
      SRT
    end

    it 'returns an empty document when no segment has subtitles' do
      composed = described_class.new.call(['', ''])

      expect(composed).to eq('')
    end
  end
end
