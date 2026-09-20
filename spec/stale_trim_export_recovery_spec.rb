# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::StaleTrimExportRecovery do
  subject(:recovery) do
    described_class.new(
      repo: repo,
      process_alive: process_alive
    )
  end

  let(:repo) do
    instance_double(
      VideoEncoder::Persistence::JobRepository
    )
  end

  let(:process_alive) { instance_double(Proc) }

  let(:active_job) do
    VideoEncoder::TrimExportJob.new(
      id: 'active',
      project_path: 'active.json',
      output_path: 'active.mkv',
      status: VideoEncoder::Status::RUNNING,
      worker_pid: 111
    )
  end

  let(:stale_job) do
    VideoEncoder::TrimExportJob.new(
      id: 'stale',
      project_path: 'stale.json',
      output_path: 'stale.mkv',
      status: VideoEncoder::Status::RUNNING,
      worker_pid: 222
    )
  end

  let(:legacy_job) do
    VideoEncoder::TrimExportJob.new(
      id: 'legacy',
      project_path: 'legacy.json',
      output_path: 'legacy.mkv',
      status: VideoEncoder::Status::RUNNING
    )
  end

  it 'interrupts only jobs without a living worker' do
    allow(repo).to receive(:running)
      .with(
        kind: VideoEncoder::TrimExportJob::KIND
      )
      .and_return(
        [
          active_job,
          stale_job,
          legacy_job
        ]
      )

    allow(process_alive).to receive(:call)
      .with(111)
      .and_return(true)

    allow(process_alive).to receive(:call)
      .with(222)
      .and_return(false)

    expect(repo).not_to receive(:mark_interrupted)
      .with(active_job, anything)

    expect(repo).to receive(:mark_interrupted)
      .with(
        stale_job,
        'trim export worker stopped unexpectedly'
      )

    expect(repo).to receive(:mark_interrupted)
      .with(
        legacy_job,
        'trim export worker stopped unexpectedly'
      )

    expect(recovery.call).to be(false)
  end

  it 'allows processing after recovering stale jobs' do
    allow(repo).to receive(:running)
      .with(
        kind: VideoEncoder::TrimExportJob::KIND
      )
      .and_return([stale_job])

    allow(process_alive).to receive(:call)
      .with(222)
      .and_return(false)

    expect(repo).to receive(:mark_interrupted)
      .with(
        stale_job,
        'trim export worker stopped unexpectedly'
      )

    expect(recovery.call).to be(true)
  end
end
