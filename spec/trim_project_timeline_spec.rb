# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimProject do
  let(:media) { instance_double(VideoEncoder::Media) }

  subject(:project) do
    described_class.new(source: media)
  end
  describe '#add_gap' do
    it 'adds a gap to the timeline' do
      gap = VideoEncoder::Gap.new(frame_count: 50)

      project.add_gap(gap)

      expect(project.timeline).to eq([gap])
    end

    it 'adds a gap after the existing segments' do
      segment = VideoEncoder::Segment.new(
        source: media,
        start_frame: 1_000,
        end_frame: 2_000
      )
      gap = VideoEncoder::Gap.new(frame_count: 50)

      project.add_segment(segment)
      project.add_gap(gap)

      expect(project.timeline).to eq([segment, gap])
    end
  end

  describe '#timeline' do
    it 'is initially empty' do
      expect(project.timeline).to be_empty
    end
  end
end
