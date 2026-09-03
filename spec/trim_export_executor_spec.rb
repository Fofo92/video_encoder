# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExportExecutor do
  subject(:executor) do
    described_class.new(
      service_factory: service_factory,
      file: file,
      filesystem: filesystem
    )
  end

  let(:file) { class_double(File) }

  let(:service_factory) do
    instance_double(
      VideoEncoder::TrimProjectFileExportFactory
    )
  end

  let(:filesystem) { class_double(FileUtils) }

  let(:service) do
    instance_double(
      VideoEncoder::ExportTrimProjectFile
    )
  end

  let(:job) do
    VideoEncoder::TrimExportJob.new(
      project_path: '/projects/movie.json',
      output_path: '/exports/movie.mkv'
    )
  end

  describe '#call' do
    it 'builds a dedicated export service for the job' do
      workspace_directory =
        '/exports/video_encoder_movie_workspace'

      allow(file).to receive(:exist?)
        .with(job.output_path)
        .and_return(false)

      expect(filesystem).to receive(:mkdir_p)
        .with(workspace_directory)

      expect(service_factory).to receive(:build)
        .with(
          workspace_directory: workspace_directory
        )
        .and_return(service)

      expect(service).to receive(:call)
        .with(
          project_path: '/projects/movie.json',
          output_path: '/exports/movie.mkv'
        )

      executor.call(job)
    end

    it 'refuses to overwrite an existing output' do
      allow(file).to receive(:exist?)
        .with(job.output_path)
        .and_return(true)

      expect(filesystem).not_to receive(:mkdir_p)
      expect(service_factory).not_to receive(:build)

      expect { executor.call(job) }
        .to raise_error(
          ArgumentError,
          'output already exists: /exports/movie.mkv'
        )
    end
  end
end
