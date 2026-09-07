# frozen_string_literal: true

require 'spec_helper'
require 'json'
require 'stringio'

RSpec.describe VideoEncoder::CLI::SourceUsageCommand do
  it 'writes active source usage as JSON' do
    source_usage = instance_double(
      VideoEncoder::ActiveTrimExportSourceUsage
    )
    serializer = instance_double(
      VideoEncoder::CLI::JobSerializer
    )
    output = StringIO.new

    job = VideoEncoder::TrimExportJob.new(
      id: 'trim-1',
      project_path: '/projects/movie.json',
      output_path: '/videos/movie.mkv',
      status: VideoEncoder::Status::QUEUED
    )

    allow(source_usage).to receive(:call)
      .with('/commun/to_be_cut/movie.m2t')
      .and_return([job])

    allow(serializer).to receive(:call)
      .with(job)
      .and_return(
        id: 'trim-1',
        status: 'queued'
      )

    command = described_class.new(
      argv: ['/commun/to_be_cut/movie.m2t'],
      source_usage: source_usage,
      serializer: serializer,
      output: output
    )

    command.run

    expect(JSON.parse(output.string)).to eq(
      'format' => 'video_encoder.source_usage',
      'version' => 1,
      'source' => '/commun/to_be_cut/movie.m2t',
      'active_jobs' => [
        {
          'id' => 'trim-1',
          'status' => 'queued'
        }
      ]
    )
  end
end
