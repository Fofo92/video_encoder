# frozen_string_literal: true

require_relative 'database'
require 'json'
require 'securerandom'

module VideoEncoder
  module Persistence
    # JobRepository manages persistence of encoding jobs in the database.
    class JobRepository
      # Validation conflicts must not be classified as SQLite driver errors.
      class QueueActionError < StandardError; end

      def initialize(db)
        @db = db
        @jobs = db[:jobs]
      end

      def enqueue(job)
        @jobs.insert(
          persistence_attributes(job)
        )
      end

      def next(kind: TrimExportJob::KIND)
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

      def running(kind:)
        @jobs
          .where(
            status: Status::RUNNING,
            kind: kind
          )
          .order(:id)
          .all
          .map do |row|
            build_job(row)
          end
      end

      def mark_running(
        job,
        worker_pid: Process.pid
      )
        @jobs.where(job_id: job.id, status: Status::QUEUED).update(
          status: Status::RUNNING,
          started_at: Time.now,
          worker_pid: worker_pid,
          attempts: Sequel[:attempts] + 1
        ) == 1
      end

      def mark_done(job)
        @jobs.where(job_id: job.id).update(
          status: Status::DONE,
          worker_pid: nil,
          finished_at: Time.now
        )
      end

      def mark_failed(job, error)
        @jobs.where(job_id: job.id).update(
          status: Status::FAILED,
          error: error,
          finished_at: Time.now,
          worker_pid: nil,
          attempts: Sequel[:attempts] # pas d'incrément ici
        )
      end

      def mark_interrupted(job, error)
        @jobs.where(job_id: job.id).update(
          status: Status::INTERRUPTED,
          error: error,
          finished_at: Time.now,
          worker_pid: nil,
          attempts: Sequel[:attempts]
        )
      end

      def retry(job_id)
        @jobs.where(job_id: job_id).update(
          attempts: Sequel[:attempts],
          status: Status::QUEUED,
          error: nil,
          started_at: nil,
          finished_at: nil,
          worker_pid: nil,
          created_at: Time.now
        )
      end

      def remove_queued?(job_id)
        @jobs.where(
          job_id: job_id,
          status: Status::QUEUED
        ).delete == 1
      end

      def defer_queued?(job_id)
        @jobs.where(job_id: job_id, status: Status::QUEUED)
             .update(status: Status::DEFERRED) == 1
      end

      def resume_deferred?(job_id)
        @jobs.where(job_id: job_id, status: Status::DEFERRED)
             .update(status: Status::QUEUED) == 1
      end

      def update_pending_output?(job_id, output_path)
        created_project = nil
        @db.transaction(mode: :immediate) do
          row = @jobs.where(job_id: job_id, status: [Status::QUEUED, Status::DEFERRED]).first
          next false unless row

          output = File.expand_path(output_path)
          validate_pending_output!(job_id, output)
          source = File.expand_path(row[:project_path])
          bytes = File.binread(source)
          validate_trim_project!(bytes)
          project = output.sub(/\.mkv\z/i, '.json')
          copy_project_if_needed(source, project, bytes) { |created| created_project = created }
          @jobs.where(job_id: job_id, status: [Status::QUEUED, Status::DEFERRED])
               .update(output_path: output, project_path: project) == 1
        end
      rescue StandardError
        File.delete(created_project) if created_project && File.exist?(created_project)
        raise
      end

      def delete_inactive?(job_id, delete_project: false)
        tombstone = nil
        project = nil
        removed = @db.transaction(mode: :immediate) do
          row = @jobs.where(job_id: job_id).exclude(status: Status::RUNNING).first
          next false unless row

          if delete_project
            project = File.expand_path(row[:project_path])
            validate_deletable_project!(job_id, project)
            if File.exist?(project)
              tombstone = "#{project}.removing-#{SecureRandom.uuid}"
              File.rename(project, tombstone)
            end
          end
          @jobs.where(job_id: job_id).exclude(status: Status::RUNNING).delete == 1
        end
        File.delete(tombstone) if removed && tombstone
        removed
      rescue StandardError
        File.rename(tombstone, project) if tombstone && File.exist?(tombstone) && project && !File.exist?(project)
        raise
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

      def validate_pending_output!(job_id, output)
        valid_file = File.extname(output).downcase == '.mkv' && !File.exist?(output) && !File.symlink?(output)
        raise QueueActionError, 'output must be a new .mkv file' unless valid_file
        raise QueueActionError, 'output directory does not exist' unless File.directory?(File.dirname(output))

        active = [Status::QUEUED, Status::DEFERRED, Status::RUNNING]
        collision = @jobs.exclude(job_id: job_id).where(status: active).all.any? do |job|
          canonical_output(job[:output_path]) == canonical_output(output)
        end
        raise QueueActionError, 'another pending job already uses this output' if collision
      end

      def validate_trim_project!(bytes)
        return if JSON.parse(bytes)['format'] == 'video_encoder.trim_project'

        raise QueueActionError, 'unsupported project'
      end

      def copy_project_if_needed(source, project, bytes)
        return if project == source

        if File.exist?(project)
          unless File.binread(project) == bytes
            raise QueueActionError, 'destination project already exists with different content'
          end

          return
        end

        File.open(project, File::WRONLY | File::CREAT | File::EXCL) do |file|
          yield project
          file.write(bytes)
        end
      end

      def validate_deletable_project!(job_id, project)
        shared = @jobs.exclude(job_id: job_id).all.any? do |job|
          same_project_path?(job[:project_path], project)
        end
        raise QueueActionError, 'the project is referenced by another job' if shared
        return unless File.exist?(project)

        valid = File.extname(project).downcase == '.json' && !File.symlink?(project) &&
                JSON.parse(File.read(project))['format'] == 'video_encoder.trim_project'
        raise QueueActionError, 'only a regular trim project JSON can be deleted' unless valid
      end

      def canonical_output(path)
        expanded = File.expand_path(path)
        File.join(File.realpath(File.dirname(expanded)), File.basename(expanded))
      rescue Errno::ENOENT
        expanded
      end

      def same_project_path?(left, right)
        left_path = File.expand_path(left)
        right_path = File.expand_path(right)
        return true if left_path == right_path

        File.realpath(left_path) == File.realpath(right_path)
      rescue Errno::ENOENT
        false
      end

      def persistence_attributes(job)
        unless job.is_a?(TrimExportJob)
          raise ArgumentError,
                "unsupported job: #{job.class}"
        end

        {
          job_id: job.id,
          kind: job.kind,
          status: Status::QUEUED,
          created_at: Time.now,
          attempts: 0,
          project_path: job.project_path.to_s,
          output_path: job.output_path.to_s
        }
      end

      def build_job(row)
        unless row[:kind] == TrimExportJob::KIND
          raise ArgumentError,
                'unsupported job kind: ' \
                "#{row[:kind]}"
        end

        attributes = {
          id: row[:job_id],
          status: row[:status],
          attempts: row[:attempts] || 0,
          created_at: row[:created_at],
          started_at: row[:started_at],
          finished_at: row[:finished_at],
          error: row[:error],
          worker_pid: row[:worker_pid]
        }

        TrimExportJob.new(
          project_path: row[:project_path],
          output_path: row[:output_path],
          **attributes
        )
      end
    end
  end
end
