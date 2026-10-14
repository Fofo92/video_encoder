# frozen_string_literal: true

require 'tmpdir'
require 'json'

RSpec.describe VideoEncoder::Persistence::JobRepository do
  subject(:repo) { described_class.new(test_db) }

  around do |example|
    Dir.mktmpdir do |directory|
      @directory = directory
      example.run
    end
  end

  let(:project) { File.join(@directory, 'source.json') }
  let(:output) { File.join(@directory, 'source.mkv') }
  let(:job) { VideoEncoder::TrimExportJob.new(project_path: project, output_path: output) }

  before do
    File.write(project, JSON.generate(format: 'video_encoder.trim_project', version: 2, timeline: []))
    repo.enqueue(job)
  end

  it 'keeps a deferred task with the same identity, but skips it during execution' do
    expect(repo.defer_queued?(job.id)).to be(true)
    expect(repo.find(job.id).status).to eq(VideoEncoder::Status::DEFERRED)
    expect(repo.next).to be_nil
    expect(File.exist?(project)).to be(true)
    expect(repo.resume_deferred?(job.id)).to be(true)
    expect(repo.next.id).to eq(job.id)
    expect(repo.find(job.id).attempts).to eq(0)
  end

  it 'does not claim a job after it was deferred by another process' do
    selected = repo.next
    repo.defer_queued?(job.id)
    expect(repo.mark_running(selected)).to be(false)
    expect(repo.find(job.id).attempts).to eq(0)
  end

  it 'does not change or delete a running job' do
    expect(repo.mark_running(job)).to be(true)
    expect(repo.defer_queued?(job.id)).to be(false)
    expect(repo.resume_deferred?(job.id)).to be(false)
    expect(repo.delete_inactive?(job.id, delete_project: true)).to be(false)
    expect(repo.update_pending_output?(job.id, File.join(@directory, 'renamed.mkv'))).to be(false)
    expect(File.exist?(project)).to be(true)
    expect(repo.find(job.id)).to be_running
  end

  it 'allows only one worker to claim a pending job' do
    expect(repo.mark_running(job)).to be(true)
    expect(repo.mark_running(job)).to be(false)
    expect(repo.find(job.id).attempts).to eq(1)
  end

  it 'changes the output and creates its matching JSON without removing the original' do
    destination = File.join(@directory, 'renamed.mkv')
    expect(repo.update_pending_output?(job.id, destination)).to be(true)
    changed = repo.find(job.id)
    expect(changed.output_path.to_s).to eq(destination)
    expect(changed.project_path.to_s).to eq(File.join(@directory, 'renamed.json'))
    expect(File.read(changed.project_path)).to eq(File.read(project))
    expect(File.exist?(project)).to be(true)
  end

  it 'also changes the destination of a deferred job without reactivating it' do
    repo.defer_queued?(job.id)
    expect(repo.update_pending_output?(job.id, File.join(@directory, 'later.mkv'))).to be(true)
    expect(repo.find(job.id).status).to eq(VideoEncoder::Status::DEFERRED)
  end

  it 'does not overwrite an existing video' do
    File.write(output, 'existing video')
    expect { repo.update_pending_output?(job.id, output) }.to raise_error(described_class::QueueActionError)
    expect(File.read(output)).to eq('existing video')
  end

  it 'does not overwrite a different JSON at the destination' do
    destination = File.join(@directory, 'renamed.mkv')
    File.write(File.join(@directory, 'renamed.json'), 'different project')
    expect { repo.update_pending_output?(job.id, destination) }.to raise_error(described_class::QueueActionError)
    expect(repo.find(job.id).output_path.to_s).to eq(output)
    expect(File.read(File.join(@directory, 'renamed.json'))).to eq('different project')
  end

  it 'rejects an output already reserved by another pending task' do
    other = VideoEncoder::TrimExportJob.new(project_path: project, output_path: File.join(@directory, 'reserved.mkv'))
    repo.enqueue(other)
    expect { repo.update_pending_output?(job.id, other.output_path.to_s) }
      .to raise_error(described_class::QueueActionError)
    expect(repo.find(job.id).output_path.to_s).to eq(output)
  end

  it 'deletes only the task by default' do
    File.write(output, 'encoded')
    expect(repo.delete_inactive?(job.id)).to be(true)
    expect(repo.find(job.id)).to be_nil
    expect(File.exist?(project)).to be(true)
    expect(File.read(output)).to eq('encoded')
  end

  it 'deletes the task and JSON only when explicitly requested' do
    File.write(output, 'encoded')
    expect(repo.delete_inactive?(job.id, delete_project: true)).to be(true)
    expect(repo.find(job.id)).to be_nil
    expect(File.exist?(project)).to be(false)
    expect(File.read(output)).to eq('encoded')
  end

  it 'preserves a shared JSON and its tasks' do
    other = VideoEncoder::TrimExportJob.new(project_path: project, output_path: File.join(@directory, 'other.mkv'))
    repo.enqueue(other)
    expect { repo.delete_inactive?(job.id, delete_project: true) }
      .to raise_error(described_class::QueueActionError, /another job/)
    expect(repo.find(job.id)).not_to be_nil
    expect(File.exist?(project)).to be(true)
  end
end
