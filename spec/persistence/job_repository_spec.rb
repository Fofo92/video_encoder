# frozen_string_literal: true

RSpec.describe VideoEncoder::Persistence::JobRepository do
  subject(:repo) { described_class.new(test_db) }

  let(:job) do
    VideoEncoder::TrimExportJob.new(
      project_path: 'movie.json',
      output_path: 'movie.mkv'
    )
  end

  describe '#enqueue' do
    it 'stores a trim export job' do
      repo.enqueue(job)

      stored_job = repo.find(job.id)

      expect(stored_job).to be_a(
        VideoEncoder::TrimExportJob
      )
      expect(stored_job.id).to eq(job.id)
      expect(stored_job.kind).to eq('trim_export')
      expect(stored_job.project_path).to eq(
        Pathname('movie.json')
      )
      expect(stored_job.output_path).to eq(
        Pathname('movie.mkv')
      )
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

        expect(found_job).to be_a(
          VideoEncoder::TrimExportJob
        )
        expect(found_job.id).to eq(job.id)
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
      first_job = job
      second_job = VideoEncoder::TrimExportJob.new(
        project_path: 'second.json',
        output_path: 'second.mkv'
      )

      repo.enqueue(first_job)
      repo.enqueue(second_job)

      expect(repo.all.map(&:id)).to contain_exactly(
        first_job.id,
        second_job.id
      )
    end
  end

  describe '#next' do
    it 'returns nil when there are no queued jobs' do
      expect(repo.next).to be_nil
    end

    it 'returns the first queued trim export' do
      repo.enqueue(job)

      expect(repo.next.id).to eq(job.id)
    end

    it 'does not return jobs that are already running' do
      repo.enqueue(job)
      repo.mark_running(job)

      expect(repo.next).to be_nil
    end
  end

  describe '#mark_running' do
    it 'marks the job as running and increments attempts' do
      repo.enqueue(job)

      repo.mark_running(job)

      stored_job = repo.find(job.id)

      expect(stored_job).to be_running
      expect(stored_job.attempts).to eq(1)
      expect(stored_job.started_at).not_to be_nil
    end

    it 'increments attempts each time the job starts' do
      repo.enqueue(job)

      repo.mark_running(job)
      repo.retry(job.id)
      repo.mark_running(job)

      expect(repo.find(job.id).attempts).to eq(2)
    end
  end

  describe '#mark_done' do
    it 'marks the job as done' do
      repo.enqueue(job)
      repo.mark_running(job)

      repo.mark_done(job)

      stored_job = repo.find(job.id)

      expect(stored_job).to be_done
      expect(stored_job.finished_at).not_to be_nil
    end
  end

  describe '#mark_failed' do
    it 'marks the job as failed' do
      repo.enqueue(job)
      repo.mark_running(job)

      repo.mark_failed(job, 'boom')

      stored_job = repo.find(job.id)

      expect(stored_job).to be_failed
      expect(stored_job.error).to eq('boom')
      expect(stored_job.finished_at).not_to be_nil
      expect(stored_job.attempts).to eq(1)
    end
  end

  describe '#retry' do
    it 'puts the job back in the queue' do
      repo.enqueue(job)
      repo.mark_running(job)
      repo.mark_failed(job, 'boom')

      repo.retry(job.id)

      stored_job = repo.find(job.id)

      expect(stored_job).to be_queued
      expect(stored_job.error).to be_nil
      expect(stored_job.started_at).to be_nil
      expect(stored_job.finished_at).to be_nil
      expect(stored_job.attempts).to eq(1)
    end
  end

  describe 'trim export lifecycle' do
    it 'tracks failure, retry and completion' do
      repo.enqueue(job)
      repo.mark_running(job)
      repo.mark_failed(job, 'temporary failure')

      failed = repo.find(job.id)

      expect(failed).to be_failed
      expect(failed.error).to eq('temporary failure')
      expect(failed.attempts).to eq(1)

      repo.retry(job.id)
      repo.mark_running(job)
      repo.mark_done(job)

      completed = repo.find(job.id)

      expect(completed).to be_done
      expect(completed.error).to be_nil
      expect(completed.attempts).to eq(2)
      expect(completed.finished_at).not_to be_nil
    end
  end
end
