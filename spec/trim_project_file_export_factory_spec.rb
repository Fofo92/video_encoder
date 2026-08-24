# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimProjectFileExportFactory do
  describe '#build' do
    it 'builds a persisted project export service' do
      runner = instance_double(VideoEncoder::CommandRunner)
      media_probe = instance_double(VideoEncoder::MediaProbe)

      factory = described_class.new(
        runner: runner,
        media_probe: media_probe,
        reader: File,
        ccextractor_executable: 'ccextractor',
        synchronization_delay: 0
      )

      service = factory.build(
        workspace_directory: '/tmp/video_encoder_workspace'
      )

      expect(service).to be_a(VideoEncoder::ExportTrimProjectFile)
    end
  end
end
