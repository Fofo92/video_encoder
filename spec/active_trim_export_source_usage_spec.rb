# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ActiveTrimExportSourceUsage do
  subject(:usage) do
    described_class.new(
      repo: repo,
      reader: reader,
      source_paths: source_paths
    )
  end

  let(:repo) { instance_double('JobRepository') }
  let(:reader) { class_double(File) }

  let(:source_paths) do
    instance_double(
      VideoEncoder::TrimProjectSourcePaths
    )
  end

  let(:queued_job) do
    VideoEncoder::TrimExportJob.new(
      project_path: '/projects/queued.json',
      output_path: '/videos/queued.mkv',
      status: VideoEncoder::Status::QUEUED
    )
  end

  let(:running_job) do
    VideoEncoder::TrimExportJob.new(
      project_path: '/projects/running.json',
      output_path: '/videos/running.mkv',
      status: VideoEncoder::Status::RUNNING
    )
  end

  let(:done_job) do
    VideoEncoder::TrimExportJob.new(
      project_path: '/projects/done.json',
      output_path: '/videos/done.mkv',
      status: VideoEncoder::Status::DONE
    )
  end

  it 'returns active jobs using the source' do
    allow(repo).to receive(:all).and_return(
      [queued_job, running_job, done_job]
    )

    allow(reader).to receive(:read)
      .with(queued_job.project_path)
      .and_return('queued project')

    allow(reader).to receive(:read)
      .with(running_job.project_path)
      .and_return('running project')

    allow(source_paths).to receive(:call)
      .with('queued project')
      .and_return(
        [Pathname('/commun/to_be_cut/movie.m2t')]
      )

    allow(source_paths).to receive(:call)
      .with('running project')
      .and_return(
        [Pathname('/commun/to_be_cut/other.m2t')]
      )

    expect(
      usage.call(
        '/commun/to_be_cut/movie.m2t'
      )
    ).to eq([queued_job])

    expect(reader).not_to have_received(:read)
      .with(done_job.project_path)
  end
end
