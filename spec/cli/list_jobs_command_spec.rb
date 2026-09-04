# frozen_string_literal: true

require 'json'
require 'spec_helper'
require 'stringio'

RSpec.describe VideoEncoder::CLI::ListJobsCommand do
  let(:repo) do
    instance_double(
      VideoEncoder::Persistence::JobRepository,
      all: [job]
    )
  end

  let(:job) do
    VideoEncoder::TrimExportJob.new(
      id: 'trim-1',
      project_path: '/commun/movie.json',
      output_path: '/videos/movie.mkv',
      status: VideoEncoder::Status::QUEUED,
      attempts: 0,
      created_at: Time.utc(2026, 9, 5, 8, 0, 0)
    )
  end

  it 'writes the jobs as a versioned JSON document' do
    output = StringIO.new

    command = described_class.new(
      argv: ['--json'],
      repo: repo,
      output: output
    )

    command.run

    expect(JSON.parse(output.string)).to eq(
      'format' => 'video_encoder.job_list',
      'version' => 1,
      'jobs' => [
        {
          'id' => 'trim-1',
          'kind' => 'trim_export',
          'input_path' => '/commun/movie.json',
          'output_path' => '/videos/movie.mkv',
          'status' => 'queued',
          'attempts' => 0,
          'created_at' => '2026-09-05T08:00:00Z',
          'started_at' => nil,
          'finished_at' => nil,
          'error' => nil
        }
      ]
    )
  end
end
