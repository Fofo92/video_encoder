# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Segment do
  subject(:segment) do
    described_class.new(
      start_time: '01:02:40.000',
      end_time:   '01:03:40.000'
    )
  end

  describe '#start_time' do
    it 'returns the beginning of the segment' do
      expect(segment.start_time).to eq('01:02:40.000')
    end
  end

  describe '#end_time' do
    it 'returns the end of the segment' do
      expect(segment.end_time).to eq('01:03:40.000')
    end
  end

  describe '#initialize' do
    it 'rejects a segment whose end precedes its beginning' do
      expect do
        described_class.new(
          start_time: '01:03:40.000',
          end_time:   '01:02:40.000'
        )
      end.to raise_error(ArgumentError)
    end

    it 'rejects a segment with identical boundaries' do
      expect do
        described_class.new(
          start_time: '01:03:40.000',
          end_time:   '01:03:40.000'
        )
      end.to raise_error(ArgumentError)
    end
  end

  describe '#duration' do
    it 'returns the segment duration in milliseconds' do
      segment = described_class.new(
        start_time: '01:02:40.000',
        end_time:   '01:03:40.250'
      )

      expect(segment.duration).to eq(60_250)
    end
  end

  describe '#==' do
    it 'is equal to another segment with the same boundaries' do
      first = described_class.new(
        start_time: '00:10:00.000',
        end_time:   '00:11:00.000'
      )

      second = described_class.new(
        start_time: '00:10:00.000',
        end_time:   '00:11:00.000'
      )

      expect(first).to eq(second)
    end

    it 'is not equal to a segment with different boundaries' do
      first = described_class.new(
        start_time: '00:10:00.000',
        end_time:   '00:11:00.000'
      )

      second = described_class.new(
        start_time: '00:10:00.000',
        end_time:   '00:12:00.000'
      )

      expect(first).not_to eq(second)
    end
  end
  describe '#start_frame' do
    it 'returns the first frame of the segment' do
      segment = described_class.new(
        start_frame: 1_500,
        end_frame:   3_000
      )

      expect(segment.start_frame).to eq(1_500)
    end
  end

  describe '#end_frame' do
    it 'returns the last frame of the segment' do
      segment = described_class.new(
        start_frame: 1_500,
        end_frame:   3_000
      )

      expect(segment.end_frame).to eq(3_000)
    end
  end

  describe '#initialize with frames' do
    it 'rejects a segment whose end frame precedes its start frame' do
      expect do
        described_class.new(
          start_frame: 3_000,
          end_frame:   1_500
        )
      end.to raise_error(ArgumentError)
    end
  end

  describe '#frame_count' do
    it 'returns the number of frames including both boundaries' do
      segment = described_class.new(
        start_frame: 1_500,
        end_frame:   3_000
      )

      expect(segment.frame_count).to eq(1_501)
    end
  end

  describe '#source' do
    it 'returns the media from which the segment originates' do
      source = instance_double(VideoEncoder::Media)

      segment = described_class.new(
        source: source,
        start_frame: 1_000,
        end_frame: 2_000
      )

      expect(segment.source).to eq(source)
    end
  end
end
