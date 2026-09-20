# frozen_string_literal: true

module VideoEncoder
  # Recovers trim exports abandoned by a stopped worker.
  class StaleTrimExportRecovery
    ERROR_MESSAGE =
      'trim export worker stopped unexpectedly'

    def initialize(repo:, process_alive: nil)
      @repo = repo
      @process_alive = process_alive ||
                       method(:process_alive?)
    end

    def call
      active_worker = false

      repo.running(
        kind: TrimExportJob::KIND
      ).each do |job|
        if worker_alive?(job)
          active_worker = true
        else
          repo.mark_interrupted(
            job,
            ERROR_MESSAGE
          )
        end
      end

      !active_worker
    end

    private

    attr_reader :repo, :process_alive

    def worker_alive?(job)
      job.worker_pid &&
        process_alive.call(job.worker_pid)
    end

    def process_alive?(process_id)
      Process.kill(0, process_id)
      true
    rescue Errno::ESRCH
      false
    rescue Errno::EPERM
      true
    end
  end
end
