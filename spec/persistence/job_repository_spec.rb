# frozen_string_literal: true

RSpec.describe VideoEncoder::Persistence::JobRepository do
  subject(:repo) { described_class.new(test_db) }

  let(:job) { VideoEncoder::Job.new(source: 'video.mp4') }

  describe '#enqueue' do
    it 'stores a job' do
      repo.enqueue(job)

      stored_job = repo.find(job.id)

      expect(stored_job).not_to be_nil
      expect(stored_job.id).to eq(job.id)
      expect(stored_job.source).to eq(Pathname('video.mp4'))
      expect(stored_job).to be_queued
      expect(stored_job.attempts).to eq(0)
    end
  end

  describe '#find' do
    context 'when the job exists' do
      before do
        repo.enqueue(job)
      end

      it 'returns the matching job' do
        found_job = repo.find(job.id)

        expect(found_job).to be_a(VideoEncoder::Job)
        expect(found_job.id).to eq(job.id)
        expect(found_job.source).to eq(Pathname('video.mp4'))
        expect(found_job).to be_queued
      end
    end

    context 'when the job does not exist' do
      it 'returns nil' do
        expect(repo.find('unknown-id')).to be_nil
      end
    end
  end

  describe '#all' do
    it 'returns an empty collection when there are no jobs' do
      expect(repo.all).to be_empty
    end

    it 'returns all stored jobs' do
      job1 = VideoEncoder::Job.new(source: 'video1.mp4')
      job2 = VideoEncoder::Job.new(source: 'video2.mp4')

      repo.enqueue(job1)
      repo.enqueue(job2)

      jobs = repo.all

      expect(jobs.size).to eq(2)
      expect(jobs.map(&:id)).to contain_exactly(job1.id, job2.id)
    end
  end

  describe '#next' do
    it 'returns nil when there are no queued jobs' do
      expect(repo.next).to be_nil
    end

    it 'returns the first queued job' do
      repo.enqueue(job)

      next_job = repo.next

      expect(next_job).to be_a(VideoEncoder::Job)
      expect(next_job.id).to eq(job.id)
      expect(next_job).to be_queued
    end

    it 'does not return jobs that are already running' do
      repo.enqueue(job)
      repo.mark_running(job)

      expect(repo.next).to be_nil
    end
  end

  describe '#mark_running' do
    before do
      repo.enqueue(job)
      repo.mark_running(job)
    end

    it 'marks the job as running' do
      stored_job = repo.find(job.id)

      expect(stored_job).to be_running
      expect(stored_job.attempts).to eq(1)
      expect(stored_job.started_at).not_to be_nil
    end
  end

  describe '#mark_done' do
    before do
      repo.enqueue(job)
      repo.mark_running(job)
      repo.mark_done(job)
    end

    it 'marks the job as done' do
      stored_job = repo.find(job.id)

      expect(stored_job).to be_done
      expect(stored_job.finished_at).not_to be_nil
    end
  end

  describe '#mark_failed' do
    before do
      repo.enqueue(job)
      repo.mark_running(job)
      repo.mark_failed(job, 'boom')
    end

    it 'marks the job as failed' do
      stored_job = repo.find(job.id)

      expect(stored_job).to be_failed
      expect(stored_job.error).to eq('boom')
      expect(stored_job.finished_at).not_to be_nil
      expect(stored_job.attempts).to eq(1)
    end
  end

  describe '#retry' do
    before do
      repo.enqueue(job)
      repo.mark_running(job)
      repo.mark_failed(job, 'boom')

      repo.retry(job.id)
    end

    it 'puts the job back in the queue' do
      stored_job = repo.find(job.id)

      expect(stored_job).to be_queued
      expect(stored_job.error).to be_nil
      expect(stored_job.started_at).to be_nil
      expect(stored_job.finished_at).to be_nil
      expect(stored_job.attempts).to eq(1)
    end
  end

  describe '#mark_running' do
    it 'increments attempts each time the job starts' do
      repo.enqueue(job)

      repo.mark_running(job)
      repo.retry(job.id)
      repo.mark_running(job)

      stored_job = repo.find(job.id)

      expect(stored_job.attempts).to eq(2)
    end
  end
end
