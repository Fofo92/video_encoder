# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::VideoTimelineOffsetProbe do
  it 'compares source and rendered frame sequences' do
    source_frames = [
      [0, 1],
      [2, 3]
    ]

    rendered_frames = [
      [2, 3],
      [0, 0]
    ]

    extractor = instance_double(
      VideoEncoder::VideoFrameSequenceExtractor
    )

    correlator = instance_double(
      VideoEncoder::VideoTimelineCorrelator
    )

    allow(extractor).to receive(:call)
      .and_return(
        source_frames,
        rendered_frames
      )

    result = {
      offset_seconds: -0.04,
      confidence: 0.99
    }

    allow(correlator).to receive(:call)
      .with(
        source: source_frames,
        rendered: rendered_frames
      )
      .and_return(result)

    probe = described_class.new(
      extractor: extractor,
      correlator: correlator,
      sample_duration_seconds: 12.0
    )

    expect(
      probe.call(
        source_path: '/commun/source.m2t',
        source_stream_index: 0,
        source_start_seconds: 10.0,
        rendered_path: '/tmp/video.mkv',
        rendered_stream_index: 0,
        rendered_start_seconds: 0.0
      )
    ).to eq(result)

    expect(extractor).to have_received(:call).with(
      path: '/commun/source.m2t',
      stream_index: 0,
      start_seconds: 10.0,
      duration_seconds: 12.0
    )

    expect(extractor).to have_received(:call).with(
      path: '/tmp/video.mkv',
      stream_index: 0,
      start_seconds: 0.0,
      duration_seconds: 12.0
    )
  end
end
