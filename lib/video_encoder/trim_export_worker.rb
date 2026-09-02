# frozen_string_literal: true

module VideoEncoder
  # Processes queued trim export jobs.
  class TrimExportWorker
    def initialize(repo:, executor:, logger:)
      @repo = repo
      @executor = executor
      @logger = logger
    end

    def run_once
      processed = 0

      loop do
        job = repo.next(
          kind: TrimExportJob::KIND
        )
        break unless job

        processed += 1
        process_job(job)
      end

      log('No queued trim exports') if processed.zero?
    end

    def run
      log('Trim export worker started')

      loop do
        run_once
        sleep 1
      end
    rescue Interrupt
      log('Stopping trim export worker...')
    end

    private

    attr_reader :repo, :executor, :logger

    def process_job(job)
      repo.mark_running(job)
      log("Start trim export #{job.id}")

      executor.call(job)

      repo.mark_done(job)
      log("Done trim export #{job.id}")
    rescue StandardError => e
      repo.mark_failed(job, e.message)
      log(
        "Failed trim export #{job.id}: " \
        "#{e.message}"
      )
    end

    def log(message)
      logger.info(
        "[TrimExportWorker] #{message}"
      )
    end
  end
end
