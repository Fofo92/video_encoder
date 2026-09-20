# frozen_string_literal: true

require 'spec_helper'

RSpec.describe(
  VideoEncoder::Persistence::JobRepository,
  'worker ownership'
) do
  subject(:repo) { described_class.new(test_db) }

  let(:encoding_job) do
    VideoEncoder::Job.new(
      source: 'video.mp4'
    )
  end

  let(:trim_export_job) do
    VideoEncoder::TrimExportJob.new(
      project_path: 'movie.json',
      output_path: 'movie.mkv'
    )
  end

  it 'records the worker process identifier' do
    repo.enqueue(trim_export_job)

    repo.mark_running(
      trim_export_job,
      worker_pid: 12_345
    )

    stored_job = repo.find(
      trim_export_job.id
    )

    expect(stored_job.worker_pid).to eq(
      12_345
    )
  end

  it 'returns running jobs of the requested kind' do
    repo.enqueue(encoding_job)
    repo.enqueue(trim_export_job)

    repo.mark_running(
      encoding_job,
      worker_pid: 111
    )
    repo.mark_running(
      trim_export_job,
      worker_pid: 222
    )

    running_jobs = repo.running(
      kind: VideoEncoder::TrimExportJob::KIND
    )

    expect(running_jobs.map(&:id)).to eq(
      [trim_export_job.id]
    )
    expect(running_jobs.first.worker_pid).to eq(
      222
    )
  end

  it 'marks an active export as interrupted' do
    repo.enqueue(trim_export_job)
    repo.mark_running(trim_export_job)

    repo.mark_interrupted(
      trim_export_job,
      'export interrupted'
    )

    stored_job = repo.find(
      trim_export_job.id
    )

    expect(stored_job).to be_interrupted
    expect(stored_job.error).to eq(
      'export interrupted'
    )
    expect(stored_job.finished_at).not_to be_nil
    expect(stored_job.worker_pid).to be_nil
    expect(stored_job.attempts).to eq(1)
  end
end
