# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'

RSpec.describe VideoEncoder::TrimExportWorker, 'selected job' do
  around do |example|
    Dir.mktmpdir do |directory|
      @db = VideoEncoder::Persistence::Database.connect(File.join(directory, 'jobs.db'))
      example.run
    ensure
      @db&.disconnect
    end
  end

  let(:repo) { VideoEncoder::Persistence::JobRepository.new(@db) }
  let(:logger) { instance_double(Logger, info: nil) }
  let(:executor) { instance_double(VideoEncoder::TrimExportExecutor) }
  let(:worker) { described_class.new(repo: repo, executor: executor, logger: logger) }
  let(:first) { VideoEncoder::TrimExportJob.new(project_path: 'first.json', output_path: 'first.mkv') }
  let(:selected) { VideoEncoder::TrimExportJob.new(project_path: 'test.json', output_path: 'test.mkv') }
  let(:last) { VideoEncoder::TrimExportJob.new(project_path: 'last.json', output_path: 'last.mkv') }

  before do
    [first, selected, last].each { |job| repo.enqueue(job) }
  end

  it 'runs only the selected job and preserves all other queue data' do
    before_rows = @db[:jobs].exclude(job_id: selected.id).order(:id).all
    expect(executor).to receive(:call).with(have_attributes(id: selected.id)).once

    worker.run_selected(selected.id)

    expect(repo.find(selected.id).status).to eq(VideoEncoder::Status::DONE)
    expect(repo.find(selected.id).attempts).to eq(1)
    expect(@db[:jobs].exclude(job_id: selected.id).order(:id).all).to eq(before_rows)
    expect(repo.next.id).to eq(first.id)
  end

  it 'stops after a failed selected job without starting another' do
    expect(executor).to receive(:call).with(have_attributes(id: selected.id)).and_raise('test failure')

    expect { worker.run_selected(selected.id) }.to raise_error(ArgumentError, /a échoué/)

    expect(repo.find(selected.id).status).to eq(VideoEncoder::Status::FAILED)
    expect(repo.find(selected.id).error).to eq('test failure')
    expect(repo.find(first.id).attempts).to eq(0)
    expect(repo.find(last.id).attempts).to eq(0)
  end

  it 'refuses a deferred job without resuming it or starting another' do
    repo.defer_queued?(selected.id)
    expect(executor).not_to receive(:call)

    expect { worker.run_selected(selected.id) }.to raise_error(ArgumentError, /en attente/)

    expect(repo.find(selected.id).status).to eq(VideoEncoder::Status::DEFERRED)
    expect(repo.next.id).to eq(first.id)
  end

  it 'refuses a missing job without falling back to the queue' do
    expect(executor).not_to receive(:call)
    expect { worker.run_selected('missing') }.to raise_error(ArgumentError, /en attente/)
    expect(repo.find(first.id).attempts).to eq(0)
  end

  it 'does not execute a task removed from the queue between selection and claim' do
    allow(repo).to receive(:mark_running) do |job|
      repo.defer_queued?(job.id)
      false
    end
    expect(executor).not_to receive(:call)

    expect { worker.run_selected(selected.id) }.to raise_error(ArgumentError, /plus disponible/)

    expect(repo.find(selected.id).status).to eq(VideoEncoder::Status::DEFERRED)
    expect(repo.find(first.id).attempts).to eq(0)
  end
end
