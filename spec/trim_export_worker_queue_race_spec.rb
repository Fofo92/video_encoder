# frozen_string_literal: true

RSpec.describe VideoEncoder::TrimExportWorker do
  it 'skips a selected job if it was deferred before claiming it' do
    job = VideoEncoder::TrimExportJob.new(project_path: 'movie.json', output_path: 'movie.mkv')
    repo = instance_double(VideoEncoder::Persistence::JobRepository)
    allow(repo).to receive(:next).and_return(job, nil)
    allow(repo).to receive(:mark_running).with(job).and_return(false)
    executor = double('executor')
    expect(executor).not_to receive(:call)
    described_class.new(repo: repo, executor: executor, logger: double(info: nil)).run_once
  end

  it 'uses the persisted destination after atomically claiming a job' do
    old = VideoEncoder::TrimExportJob.new(id: 'same', project_path: 'old.json', output_path: 'old.mkv')
    updated = VideoEncoder::TrimExportJob.new(id: 'same', project_path: 'new.json', output_path: 'new.mkv')
    repo = instance_double(VideoEncoder::Persistence::JobRepository)
    allow(repo).to receive(:next).and_return(old, nil)
    allow(repo).to receive(:mark_running).with(old).and_return(true)
    allow(repo).to receive(:find).with('same').and_return(updated)
    allow(repo).to receive(:mark_done).with(updated)
    executor = double('executor')
    expect(executor).to receive(:call).with(updated)
    described_class.new(repo: repo, executor: executor, logger: double(info: nil)).run_once
  end
end
