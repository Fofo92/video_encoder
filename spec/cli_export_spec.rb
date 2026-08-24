# frozen_string_literal: true

require 'spec_helper'
require 'fileutils'

RSpec.describe VideoEncoder::CLI do
  describe 'export' do
    it 'exports a persisted trim project' do
      service = instance_double(VideoEncoder::ExportTrimProjectFile)

      allow(service).to receive(:call)

      cli = described_class.new(
        [
          'export',
          '/projects/movie.json',
          '--output',
          '/exports/movie.mkv'
        ],
        trim_export_service: service
      )

      cli.run

      expect(service).to have_received(:call).with(
        project_path: '/projects/movie.json',
        output_path: '/exports/movie.mkv'
      )
    end

    it 'builds its default export service beside the output file' do
      factory = instance_double(
        VideoEncoder::TrimProjectFileExportFactory
      )
      service = instance_double(VideoEncoder::ExportTrimProjectFile)

      allow(VideoEncoder::TrimProjectFileExportFactory)
        .to receive(:new)
        .and_return(factory)

      allow(factory).to receive(:build)
        .with(
          workspace_directory:
            '/exports/video_encoder_movie_workspace'
        )
        .and_return(service)

      allow(service).to receive(:call)
      allow(FileUtils).to receive(:mkdir_p)

      cli = described_class.new(
        [
          'export',
          '/projects/movie.json',
          '--output',
          '/exports/movie.mkv'
        ]
      )

      cli.run

      expect(FileUtils).to have_received(:mkdir_p).with(
        '/exports/video_encoder_movie_workspace'
      )

      expect(service).to have_received(:call).with(
        project_path: '/projects/movie.json',
        output_path: '/exports/movie.mkv'
      )
    end
  end
end
