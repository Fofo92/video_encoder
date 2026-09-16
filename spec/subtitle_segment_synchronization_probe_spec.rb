# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleSegmentSynchronizationProbe do
  it 'compares rendered and subtitle transport video timelines' do
    timeline_probe = instance_double(
      VideoEncoder::VideoTimelineOffsetProbe
    )

    correction = instance_double(
      VideoEncoder::SubtitleSynchronizationCorrection
    )

    rendered_alignment = {
      offset_seconds: -2.12,
      confidence: 1.0
    }

    transport_alignment = {
      offset_seconds: -0.16,
      confidence: 0.99
    }

    allow(timeline_probe)
      .to receive(:call)
      .and_return(
        rendered_alignment,
        transport_alignment
      )

    result = {
      offset_seconds: -1.96,
      confidence: 0.99
    }

    allow(correction)
      .to receive(:call)
      .with(
        rendered_alignment: rendered_alignment,
        transport_alignment: transport_alignment
      )
      .and_return(result)

    probe = described_class.new(
      timeline_probe: timeline_probe,
      correction: correction
    )

    expect(
      probe.call(
        source_path: '/commun/source.m2t',
        source_stream_index: 0,
        source_start_seconds: 850.36,
        transport_path: '/tmp/subtitle_segment.ts',
        rendered_video_path: '/tmp/video.mkv',
        rendered_start_seconds: 60.0
      )
    ).to eq(result)

    expect(timeline_probe)
      .to have_received(:call)
      .with(
        source_path: '/commun/source.m2t',
        source_stream_index: 0,
        source_start_seconds: 850.36,
        rendered_path: '/tmp/video.mkv',
        rendered_stream_index: 0,
        rendered_start_seconds: 60.0
      )
      .ordered

    expect(timeline_probe)
      .to have_received(:call)
      .with(
        source_path: '/commun/source.m2t',
        source_stream_index: 0,
        source_start_seconds: 850.36,
        rendered_path: '/tmp/subtitle_segment.ts',
        rendered_stream_index: 0,
        rendered_start_seconds: 0.0
      )
      .ordered
  end
end
