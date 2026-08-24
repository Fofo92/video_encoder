# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::WorkspaceCleaningExporter do
  subject(:cleaning_exporter) do
    described_class.new(
      exporter: exporter,
      workspace: workspace
    )
  end

  let(:exporter) { instance_double('Exporter') }
  let(:workspace) { instance_double(VideoEncoder::TrimWorkspace) }

  describe '#call' do
    it 'cleans the workspace after a successful export' do
      allow(exporter).to receive(:call)
        .with(trim_project: :project, output_path: '/tmp/movie.mkv')
        .and_return('/tmp/movie.mkv')

      allow(workspace).to receive(:cleanup)

      result = cleaning_exporter.call(
        trim_project: :project,
        output_path: '/tmp/movie.mkv'
      )

      expect(workspace).to have_received(:cleanup).once
      expect(result).to eq('/tmp/movie.mkv')
    end

    it 'keeps the workspace when the export fails' do
      allow(exporter).to receive(:call)
        .and_raise(RuntimeError, 'export failed')

      allow(workspace).to receive(:cleanup)

      expect do
        cleaning_exporter.call(
          trim_project: :project,
          output_path: '/tmp/movie.mkv'
        )
      end.to raise_error(RuntimeError, 'export failed')

      expect(workspace).not_to have_received(:cleanup)
    end
  end
end
