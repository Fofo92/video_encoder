# frozen_string_literal: true

require 'spec_helper'

RSpec.describe 'Trim project persistence' do
  it 'round-trips a multi-source project timeline' do
    media_a = VideoEncoder::Media.new(
      path: '/commun/source-a.m2t',
      duration: 3_600
    )

    media_c = VideoEncoder::Media.new(
      path: '/commun/source-c.m2t',
      duration: 3_600
    )

    project = VideoEncoder::TrimProject.new
    project.add_segment(
      VideoEncoder::Segment.new(
        source: media_a,
        start_frame: 30_000,
        end_frame: 31_499
      )
    )
    project.add_segment(
      VideoEncoder::Segment.new(
        source: media_c,
        start_frame: 30_000,
        end_frame: 31_499
      )
    )
    project.add_gap(VideoEncoder::Gap.new(frame_count: 25))
    project.add_segment(
      VideoEncoder::Segment.new(
        source: media_a,
        start_frame: 33_000,
        end_frame: 34_499
      )
    )

    probe = instance_double(VideoEncoder::MediaProbe)

    allow(probe).to receive(:read)
      .with('/commun/source-a.m2t')
      .and_return(media_a)
    allow(probe).to receive(:read)
      .with('/commun/source-c.m2t')
      .and_return(media_c)

    json = VideoEncoder::TrimProjectSerializer.new.dump(project)

    restored = VideoEncoder::TrimProjectLoader.new(
      media_probe: probe
    ).load(json)

    expect(restored.timeline).to eq(project.timeline)
  end
end
