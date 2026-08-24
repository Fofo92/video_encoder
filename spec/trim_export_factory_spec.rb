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
  end
end
