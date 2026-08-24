# frozen_string_literal: true

require 'spec_helper'
require 'json'

RSpec.describe VideoEncoder::TrimProjectSerializer do
  describe '#dump' do
    it 'serializes the complete project timeline' do
      media = VideoEncoder::Media.new(
        path: '/commun/source-a.m2t',
        duration: 3_600
      )

      segment = VideoEncoder::Segment.new(
        source: media,
        start_frame: 30_000,
        end_frame: 31_499
      )

      project = VideoEncoder::TrimProject.new
      project.add_segment(segment)
      project.add_gap(VideoEncoder::Gap.new(frame_count: 50))

      document = JSON.parse(described_class.new.dump(project))

      expect(document).to eq(
        'format' => 'video_encoder.trim_project',
        'version' => 1,
        'timeline' => [
          {
            'type' => 'segment',
            'source' => '/commun/source-a.m2t',
            'start_frame' => 30_000,
            'end_frame' => 31_499
          },
          {
            'type' => 'gap',
            'frame_count' => 50
          }
        ]
      )
    end

    it 'rejects a segment without frame boundaries' do
      media = VideoEncoder::Media.new(
        path: '/commun/source-a.m2t',
        duration: 3_600
      )

      segment = VideoEncoder::Segment.new(
        source: media,
        start_time: '00:20:00.000',
        end_time: '00:21:00.000'
      )

      project = VideoEncoder::TrimProject.new
      project.add_segment(segment)

      expect do
        described_class.new.dump(project)
      end.to raise_error(
        ArgumentError,
        'persistent segments require frame boundaries'
      )
    end
  end
end
