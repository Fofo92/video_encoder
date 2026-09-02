# frozen_string_literal: true

require_relative 'database'

module VideoEncoder
  module Persistence
    # JobRepository manages persistence of encoding jobs in the database.
    class JobRepository
      def initialize(db)
        @jobs = db[:jobs]
      end

      def enqueue(job)
        @jobs.insert(
          persistence_attributes(job)
        )
      end

      def next(kind: Job::KIND)
        row = @jobs
              .where(
                status: Status::QUEUED,
                kind: kind
              )
              .order(:id)
              .first

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
        @jobs.all.map do |row|
          build_job(row)
        end
      end

      def find(job_id)
        row = @jobs.where(job_id: job_id).first
        return nil unless row

        build_job(row)
      end

      private

      def persistence_attributes(job)
        attributes = {
          job_id: job.id,
          kind: job.kind,
          status: Status::QUEUED,
          created_at: Time.now,
          attempts: 0
        }

        case job
        when TrimExportJob
          attributes.merge(
            project_path:
              job.project_path.to_s,
            output_path:
              job.output_path.to_s
          )
        when Job
          attributes.merge(
            source: job.source.to_s
          )
        else
          raise ArgumentError,
                "unsupported job: #{job.class}"
        end
      end

      def build_job(row)
        attributes = {
          id: row[:job_id],
          status: row[:status],
          attempts: row[:attempts] || 0,
          created_at: row[:created_at],
          started_at: row[:started_at],
          finished_at: row[:finished_at],
          error: row[:error]
        }

        case row[:kind]
        when TrimExportJob::KIND
          TrimExportJob.new(
            project_path: row[:project_path],
            output_path: row[:output_path],
            **attributes
          )
        when Job::KIND, nil
          Job.new(
            source: row[:source],
            **attributes
          )
        else
          raise ArgumentError,
                'unsupported job kind: ' \
                "#{row[:kind]}"
        end
      end
    end
  end
end
