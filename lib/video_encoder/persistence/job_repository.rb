# frozen_string_literal: true

require_relative 'database'

module VideoEncoder
  module Persistence
    # JobRepository manages persistence of encoding jobs in the database.
    class JobRepository
      def initialize(db = Database.connect('video_encoder.db'))
        @jobs = db[:jobs]
      end

      def enqueue(job)
        @jobs.insert(
          job_id: job.id,
          source: job.source.to_s,
          status: Status::QUEUED,
          created_at: Time.now,
          attempts: 0
        )
      end

      def next
        row = @jobs.where(status: Status::QUEUED).first
        return unless row

        build_job(row)
      end

      def mark_running(job)
        @jobs.where(job_id: job.id).update(
          status: Status::RUNNING,
          started_at: Time.now,
          attempts: Sequel[:attempts] + 1
        )
      end

      def mark_done(job)
        @jobs.where(job_id: job.id).update(
          status: Status::DONE,
          finished_at: Time.now
        )
      end

      def mark_failed(job, error)
        @jobs.where(job_id: job.id).update(
          status: Status::FAILED,
          error: error,
          finished_at: Time.now,
          attempts: Sequel[:attempts] # pas d'incrément ici
        )
      end

      def retry(job_id)
        @jobs.where(job_id: job_id).update(
          attempts: Sequel[:attempts],
          status: Status::QUEUED,
          error: nil,
          started_at: nil,
          finished_at: nil,
          created_at: Time.now
        )
      end

      def all
        @jobs.all
      end

      def increment_attempts(job)
        @jobs.where(job_id: job.id).update(
          attempts: Sequel[:attempts] + 1
        )
      end

      private

      def build_job(row)
        Job.new(
          id: row[:job_id],
          source: row[:source],
          status: row[:status],
          attempts: row[:attempts] || 0,
          created_at: row[:created_at],
          started_at: row[:started_at],
          finished_at: row[:finished_at],
          error: row[:error]
        )
      end
    end
  end
end
