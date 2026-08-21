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

  it 'uses the selected video track for each media source' do
    media_a = instance_double(
      VideoEncoder::Media,
      path: Pathname('/media/a.mkv')
    )

    media_c = instance_double(
      VideoEncoder::Media,
      path: Pathname('/media/c.m2t')
    )

    video_a = instance_double(VideoEncoder::VideoTrack, index: 0)
    video_c = instance_double(VideoEncoder::VideoTrack, index: 2)

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
      video_tracks_by_source: {
        media_a => video_a,
        media_c => video_c
      }
    )

    expect(xml).to include(
      <<~XML.strip,
        <chain id="source">
          <property name="resource">/media/a.mkv</property>
          <property name="video_index">0</property>
          <property name="audio_index">0</property>
        </chain>
      XML
      <<~XML.strip
        <chain id="source_1">
          <property name="resource">/media/c.m2t</property>
          <property name="video_index">2</property>
          <property name="audio_index">0</property>
        </chain>
      XML
    )
  end

  it 'uses frame boundaries for project segments' do
    media = instance_double(
      VideoEncoder::Media,
      path: Pathname('/media/movie.mkv')
    )

    project = VideoEncoder::TrimProject.new

    project.add_segment(
      VideoEncoder::Segment.new(
        source: media,
        start_frame: 1_000,
        end_frame: 2_000
      )
    )

    xml = builder.build(project)

    expect(xml).to include(
      '<entry in="1000" out="2000" producer="source"/>'
    )
  end
end
