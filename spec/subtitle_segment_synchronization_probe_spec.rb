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
        duration_seconds: 60.0,
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

  it 'retries farther into the segment after an uncertain alignment' do
    timeline_probe = instance_double(
      VideoEncoder::VideoTimelineOffsetProbe
    )

    correction = instance_double(
      VideoEncoder::SubtitleSynchronizationCorrection
    )

    uncertain_rendered = {
      offset_seconds: -2.28,
      confidence: 0.837
    }

    reliable_rendered = {
      offset_seconds: -2.12,
      confidence: 1.0
    }

    transport_alignment = {
      offset_seconds: -0.16,
      confidence: 1.0
    }

    allow(timeline_probe)
      .to receive(:call)
      .and_return(
        uncertain_rendered,
        transport_alignment,
        reliable_rendered,
        transport_alignment
      )

    expected = {
      offset_seconds: -1.96,
      confidence: 1.0
    }

    allow(correction).to receive(:call) do |rendered_alignment:, **|
      if rendered_alignment == uncertain_rendered
        raise(
          VideoEncoder::SubtitleSynchronizationCorrection::
            AlignmentUnavailable,
          'subtitle alignment confidence is too low'
        )
      end

      expected
    end

    probe = described_class.new(
      timeline_probe: timeline_probe,
      correction: correction,
      sample_offsets_seconds: [0, 15],
      sample_duration_seconds: 12
    )

    result = probe.call(
      source_path: '/commun/source.m2t',
      source_stream_index: 0,
      source_start_seconds: 1_883.44,
      duration_seconds: 60.0,
      transport_path: '/tmp/subtitle_segment.ts',
      rendered_video_path: '/tmp/video.mkv',
      rendered_start_seconds: 657.0
    )

    expect(result).to eq(expected)

    expect(timeline_probe).to have_received(:call).with(
      source_path: '/commun/source.m2t',
      source_stream_index: 0,
      source_start_seconds: 1_898.44,
      rendered_path: '/tmp/video.mkv',
      rendered_stream_index: 0,
      rendered_start_seconds: 672.0
    )

    expect(timeline_probe).to have_received(:call).with(
      source_path: '/commun/source.m2t',
      source_stream_index: 0,
      source_start_seconds: 1_898.44,
      rendered_path: '/tmp/subtitle_segment.ts',
      rendered_stream_index: 0,
      rendered_start_seconds: 15.0
    )
  end
end
