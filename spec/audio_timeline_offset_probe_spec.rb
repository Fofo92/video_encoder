# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::AudioTimelineOffsetProbe do
  it 'compares source and rendered audio envelopes' do
    source_envelope = [0.1, 0.4, 0.2, 0.8]
    rendered_envelope = [0.4, 0.2, 0.8, 0.0]

    extractor = instance_double(
      VideoEncoder::AudioEnvelopeExtractor
    )

    correlator = instance_double(
      VideoEncoder::AudioTimelineCorrelator
    )

    allow(extractor).to receive(:call)
      .and_return(
        source_envelope,
        rendered_envelope
      )

    result = {
      offset_seconds: -0.1,
      confidence: 0.99
    }

    allow(correlator).to receive(:call)
      .with(
        source: source_envelope,
        rendered: rendered_envelope
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
        source_stream_index: 1,
        source_start_seconds: 850.36,
        rendered_path: '/tmp/video.mkv',
        rendered_stream_index: 0,
        rendered_start_seconds: 0.0
      )
    ).to eq(result)

    expect(extractor).to have_received(:call).with(
      path: '/commun/source.m2t',
      stream_index: 1,
      start_seconds: 850.36,
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
