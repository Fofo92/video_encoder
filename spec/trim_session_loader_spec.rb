# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimSessionLoader do
  subject(:loader) do
    described_class.new(media_probe: media_probe)
  end

  let(:media_probe) do
    instance_double(VideoEncoder::MediaProbe)
  end

  let(:media_a) do
    VideoEncoder::Media.new(
      path: '/commun/source-a.m2t',
      duration: 3_600
    )
  end

  let(:media_c) do
    VideoEncoder::Media.new(
      path: '/commun/source-c.m2t',
      duration: 600
    )
  end

  let(:json) do
    JSON.generate(
      format: 'video_encoder.trim_session',
      version: 1,
      sources: [
        {
          id: 'A',
          path: '/commun/source-a.m2t'
        },
        {
          id: 'C',
          path: '/commun/source-c.m2t'
        }
      ],
      timeline: [
        {
          source_id: 'A',
          start_frame: 0,
          end_frame: 1_499
        },
        {
          source_id: 'C',
          start_frame: 3_000,
          end_frame: 4_499
        },
        {
          source_id: 'A',
          start_frame: 5_000,
          end_frame: 7_999
        }
      ]
    )
  end

  before do
    allow(media_probe).to receive(:read)
      .with('/commun/source-a.m2t')
      .and_return(media_a)

    allow(media_probe).to receive(:read)
      .with('/commun/source-c.m2t')
      .and_return(media_c)
  end

  it 'builds the project in editing order' do
    project = loader.load(json)

    expect(
      project.segments.map do |segment|
        [
          segment.source.path.to_s,
          segment.start_frame,
          segment.end_frame
        ]
      end
    ).to eq(
      [
        ['/commun/source-a.m2t', 0, 1_499],
        ['/commun/source-c.m2t', 3_000, 4_499],
        ['/commun/source-a.m2t', 5_000, 7_999]
      ]
    )
  end

  it 'probes every declared source only once' do
    loader.load(json)

    expect(media_probe).to have_received(:read)
      .with('/commun/source-a.m2t')
      .once

    expect(media_probe).to have_received(:read)
      .with('/commun/source-c.m2t')
      .once
  end

  it 'rejects duplicate source identifiers' do
    duplicate_sources = JSON.generate(
      format: 'video_encoder.trim_session',
      version: 1,
      sources: [
        { id: 'A', path: '/commun/source-a.m2t' },
        { id: 'A', path: '/commun/other-source.m2t' }
      ],
      timeline: []
    )

    expect do
      loader.load(duplicate_sources)
    end.to raise_error(
      ArgumentError,
      'duplicate source identifier: A'
    )
  end

  it 'rejects an unknown source identifier in the timeline' do
    unknown_source = JSON.generate(
      format: 'video_encoder.trim_session',
      version: 1,
      sources: [],
      timeline: [
        {
          source_id: 'C',
          start_frame: 3_000,
          end_frame: 4_499
        }
      ]
    )

    expect do
      loader.load(unknown_source)
    end.to raise_error(
      ArgumentError,
      'unknown source identifier: C'
    )
  end
end
