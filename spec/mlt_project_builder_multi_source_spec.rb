# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::MltProjectBuilder do
  subject(:builder) { described_class.new }

  describe '#build' do
    it 'uses the selected audio track for each media source' do
      media_a = instance_double(
        VideoEncoder::Media,
        path: Pathname('/media/a.mkv')
      )

      media_c = instance_double(
        VideoEncoder::Media,
        path: Pathname('/media/c.m2t')
      )

      audio_a = instance_double(VideoEncoder::Track, index: 1)
      audio_c = instance_double(VideoEncoder::Track, index: 3)

      project = VideoEncoder::TrimProject.new

      project.add_segment(
        VideoEncoder::Segment.new(
          source: media_a,
          start_time: '00:00:00.000',
          end_time: '00:00:10.000'
        )
      )

      project.add_segment(
        VideoEncoder::Segment.new(
          source: media_c,
          start_time: '00:01:00.000',
          end_time: '00:01:10.000'
        )
      )

      xml = builder.build(
        project,
        audio_tracks_by_source: {
          media_a => audio_a,
          media_c => audio_c
        }
      )

      expect(xml).to include(
        <<~XML.strip,
          <chain id="source">
            <property name="resource">/media/a.mkv</property>
            <property name="video_index">0</property>
            <property name="audio_index">1</property>
          </chain>
        XML
        <<~XML.strip
          <chain id="source_1">
            <property name="resource">/media/c.m2t</property>
            <property name="video_index">0</property>
            <property name="audio_index">3</property>
          </chain>
        XML
      )
    end
  end
end
