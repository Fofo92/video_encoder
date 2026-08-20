# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimProject do
  # testing global TrimProject rules, not specific to a single source
  let(:media) { instance_double(VideoEncoder::Media) }
  let(:media_a) { instance_double(VideoEncoder::Media) }
  let(:media_c) { instance_double(VideoEncoder::Media) }

  subject(:project) { described_class.new }

  describe 'multiple sources' do
    it 'accepts segments from different media sources' do
      media_a = instance_double(VideoEncoder::Media)
      media_c = instance_double(VideoEncoder::Media)

      first = VideoEncoder::Segment.new(
        source: media_a,
        start_frame: 1_000,
        end_frame: 2_000
      )

      second = VideoEncoder::Segment.new(
        source: media_c,
        start_frame: 500,
        end_frame: 1_500
      )

      project.add_segment(first)
      project.add_segment(second)

      expect(project.timeline).to eq([first, second])
    end

    it 'builds a timeline from segments belonging to multiple sources' do
      media_a = instance_double(VideoEncoder::Media)
      media_c = instance_double(VideoEncoder::Media)

      project = described_class.new

      segment_a = VideoEncoder::Segment.new(
        source: media_a,
        start_frame: 0,
        end_frame: 1_999
      )

      segment_c = VideoEncoder::Segment.new(
        source: media_c,
        start_frame: 500,
        end_frame: 999
      )

      segment_b = VideoEncoder::Segment.new(
        source: media_a,
        start_frame: 3_000,
        end_frame: 4_999
      )

      project.add_segment(segment_a)
      project.add_segment(segment_c)
      project.add_segment(segment_b)

      expect(project.timeline).to eq(
        [segment_a, segment_c, segment_b]
      )
    end
  end
end
