# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExportFactory do
  describe '#build' do
    it 'builds the trim export application service' do
      runner = instance_double(VideoEncoder::CommandRunner)
      allow(VideoEncoder::WorkspaceCleaningExporter)
        .to receive(:new)
        .and_call_original

      factory = described_class.new(
        runner: runner,
        ccextractor_executable: 'ccextractor',
        synchronization_delay: 0.65
      )

      service = factory.build(
        workspace_directory: '/tmp/video_encoder_workspace'
      )

      expect(service).to be_a(VideoEncoder::ExportTrimProject)
      expect(VideoEncoder::WorkspaceCleaningExporter)
        .to have_received(:new)
        .with(
          exporter: an_instance_of(VideoEncoder::TrimExporter),
          workspace: an_instance_of(VideoEncoder::TrimWorkspace)
        )
    end

    it 'configures subtitle timeline synchronization' do
      runner = instance_double(
        VideoEncoder::CommandRunner
      )

      [
        VideoEncoder::VideoFrameSequenceExtractor,
        VideoEncoder::VideoTimelineCorrelator,
        VideoEncoder::VideoTimelineOffsetProbe,
        VideoEncoder::SubtitleSynchronizationCorrection,
        VideoEncoder::SubtitleSegmentSynchronizationProbe
      ].each do |component|
        allow(component)
          .to receive(:new)
          .and_call_original
      end

      factory = described_class.new(
        runner: runner,
        ccextractor_executable: 'ccextractor',
        synchronization_delay: 0.65
      )

      factory.build(
        workspace_directory:
          '/tmp/video_encoder_workspace'
      )

      expect(
        VideoEncoder::VideoFrameSequenceExtractor
      ).to have_received(:new).with(
        width: 32,
        height: 18,
        frame_rate: 25,
        seek_preroll_seconds: 5.0
      )

      expect(
        VideoEncoder::VideoTimelineCorrelator
      ).to have_received(:new).with(
        frame_rate: 25,
        maximum_shift_seconds: 3.0
      )

      expect(
        VideoEncoder::VideoTimelineOffsetProbe
      ).to have_received(:new).with(
        extractor: an_instance_of(
          VideoEncoder::VideoFrameSequenceExtractor
        ),
        correlator: an_instance_of(
          VideoEncoder::VideoTimelineCorrelator
        ),
        sample_duration_seconds: 12.0
      )

      expect(
        VideoEncoder::SubtitleSynchronizationCorrection
      ).to have_received(:new).with(
        minimum_confidence: 0.95
      )

      expect(
        VideoEncoder::SubtitleSegmentSynchronizationProbe
      ).to have_received(:new).with(
        timeline_probe: an_instance_of(
          VideoEncoder::VideoTimelineOffsetProbe
        ),
        correction: an_instance_of(
          VideoEncoder::SubtitleSynchronizationCorrection
        )
      )
    end
  end
end
