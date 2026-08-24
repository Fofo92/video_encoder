# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ExportTrimProjectFile do
  describe '#call' do
    it 'loads and exports a persisted trim project' do
      reader = instance_double('ProjectFileReader')
      loader = instance_double(VideoEncoder::TrimProjectLoader)
      exporter = instance_double(VideoEncoder::ExportTrimProject)
      project = instance_double(VideoEncoder::TrimProject)

      allow(reader).to receive(:read)
        .with('/projects/movie.json')
        .and_return('project json')

      allow(loader).to receive(:load)
        .with('project json')
        .and_return(project)

      allow(exporter).to receive(:call)

      service = described_class.new(
        reader: reader,
        loader: loader,
        exporter: exporter
      )

      service.call(
        project_path: '/projects/movie.json',
        output_path: '/exports/movie.mkv'
      )

      expect(exporter).to have_received(:call).with(
        trim_project: project,
        output_path: '/exports/movie.mkv'
      )
    end
  end
end
