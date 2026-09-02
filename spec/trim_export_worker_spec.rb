# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExportWorker do
  subject(:worker) do
    described_class.new(
      repo: repo,
      executor: executor,
      logger: logger
    )
  end

  let(:repo) do
    instance_double(
      VideoEncoder::Persistence::JobRepository
    )
  end

  let(:executor) { instance_double('TrimExportExecutor') }
  let(:logger) { instance_double(Logger, info: nil) }

  let(:job) do
    VideoEncoder::TrimExportJob.new(
      id: 'trim-1',
      project_path: 'movie.json',
      output_path: 'movie.mkv'
    )
  end

  describe '#run_once' do
    before do
      allow(repo).to receive(:next)
        .with(
          kind: VideoEncoder::TrimExportJob::KIND
        )
        .and_return(job, nil)
    end

    it 'processes a queued trim export' do
      allow(executor).to receive(:call)

      expect(repo).to receive(:mark_running)
        .with(job)
        .ordered
      expect(executor).to receive(:call)
        .with(job)
        .ordered
      expect(repo).to receive(:mark_done)
        .with(job)
        .ordered

      worker.run_once
    end

    it 'continues with the next job after a failed export' do
      next_job = VideoEncoder::TrimExportJob.new(
        id: 'trim-2',
        project_path: 'next.json',
        output_path: 'next.mkv'
      )

      allow(repo).to receive(:next)
        .with(
          kind: VideoEncoder::TrimExportJob::KIND
        )
        .and_return(job, next_job, nil)

      allow(repo).to receive(:mark_running)

      allow(executor).to receive(:call) do |current_job|
        raise 'export failed' if current_job == job
      end

      expect(repo).to receive(:mark_failed)
        .with(job, 'export failed')

      expect(repo).not_to receive(:mark_done)
        .with(job)

      expect(repo).to receive(:mark_done)
        .with(next_job)

      worker.run_once
    end
  end
end
