# frozen_string_literal: true

require 'spec_helper'
require 'json'

RSpec.describe VideoEncoder::TrimProjectSerializer do
  describe '#dump' do
    it 'serializes sources and the complete project timeline' do
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
      project.add_gap(
        VideoEncoder::Gap.new(frame_count: 50)
      )

      document = JSON.parse(
        described_class.new.dump(project)
      )

      expect(document).to eq(
        'format' => 'video_encoder.trim_project',
        'version' => 2,
        'sources' => [
          {
            'id' => 'source',
            'path' => '/commun/source-a.m2t',
            'inspection' => {
              'duration' => 3_600
            }
          }
        ],
        'timeline' => [
          {
            'type' => 'segment',
            'source_id' => 'source',
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

    it 'identifies every source once in editing order' do
      media_a = VideoEncoder::Media.new(
        path: '/commun/source-a.m2t',
        duration: 3_600
      )
      media_c = VideoEncoder::Media.new(
        path: '/commun/source-c.m2t',
        duration: 600
      )

      project = VideoEncoder::TrimProject.new
      project.add_segment(
        VideoEncoder::Segment.new(
          source: media_a,
          start_frame: 0,
          end_frame: 1_499
        )
      )
      project.add_segment(
        VideoEncoder::Segment.new(
          source: media_c,
          start_frame: 3_000,
          end_frame: 4_499
        )
      )
      project.add_segment(
        VideoEncoder::Segment.new(
          source: media_a,
          start_frame: 5_000,
          end_frame: 7_999
        )
      )

      document = JSON.parse(
        described_class.new.dump(project)
      )

      expect(document.fetch('sources')).to eq(
        [
          {
            'id' => 'source',
            'path' => '/commun/source-a.m2t',
            'inspection' => {
              'duration' => 3_600
            }
          },
          {
            'id' => 'source_1',
            'path' => '/commun/source-c.m2t',
            'inspection' => {
              'duration' => 600
            }
          }
        ]
      )

      expect(document.fetch('timeline')).to eq(
        [
          {
            'type' => 'segment',
            'source_id' => 'source',
            'start_frame' => 0,
            'end_frame' => 1_499
          },
          {
            'type' => 'segment',
            'source_id' => 'source_1',
            'start_frame' => 3_000,
            'end_frame' => 4_499
          },
          {
            'type' => 'segment',
            'source_id' => 'source',
            'start_frame' => 5_000,
            'end_frame' => 7_999
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
