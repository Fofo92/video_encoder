# frozen_string_literal: true

require 'spec_helper'
require 'json'

RSpec.describe VideoEncoder::TrimProjectLoader do
  describe '#load' do
    it 'rebuilds a trim project and probes its media sources' do
      probe = instance_double(VideoEncoder::MediaProbe)
      media = instance_double(VideoEncoder::Media)

      allow(probe).to receive(:read)
        .with('/commun/source-a.m2t')
        .and_return(media)

      document = JSON.generate(
        format: 'video_encoder.trim_project',
        version: 1,
        timeline: [
          {
            type: 'segment',
            source: '/commun/source-a.m2t',
            start_frame: 30_000,
            end_frame: 31_499
          },
          {
            type: 'gap',
            frame_count: 50
          }
        ]
      )

      project = described_class.new(media_probe: probe).load(document)

      expect(project.timeline).to eq(
        [
          VideoEncoder::Segment.new(
            source: media,
            start_frame: 30_000,
            end_frame: 31_499
          ),
          VideoEncoder::Gap.new(frame_count: 50)
        ]
      )
    end

    it 'rejects an unsupported document version' do
      probe = instance_double(VideoEncoder::MediaProbe)

      document = JSON.generate(
        format: 'video_encoder.trim_project',
        version: 2,
        timeline: []
      )

      expect do
        described_class.new(media_probe: probe).load(document)
      end.to raise_error(
        ArgumentError,
        'unsupported trim project version: 2'
      )
    end

    it 'rejects another document format' do
      probe = instance_double(VideoEncoder::MediaProbe)

      document = JSON.generate(
        format: 'another.application',
        version: 1,
        timeline: []
      )

      expect do
        described_class.new(media_probe: probe).load(document)
      end.to raise_error(
        ArgumentError,
        'unsupported document format: another.application'
      )
    end

    it 'probes a reused media source only once' do
      probe = instance_double(VideoEncoder::MediaProbe)
      media = instance_double(VideoEncoder::Media)

      allow(probe).to receive(:read)
        .with('/commun/source-a.m2t')
        .and_return(media)

      document = JSON.generate(
        format: 'video_encoder.trim_project',
        version: 1,
        timeline: [
          {
            type: 'segment',
            source: '/commun/source-a.m2t',
            start_frame: 1_000,
            end_frame: 1_999
          },
          {
            type: 'segment',
            source: '/commun/source-a.m2t',
            start_frame: 3_000,
            end_frame: 3_999
          }
        ]
      )

      described_class.new(media_probe: probe).load(document)

      expect(probe).to have_received(:read)
        .with('/commun/source-a.m2t')
        .once
    end
  end
end
