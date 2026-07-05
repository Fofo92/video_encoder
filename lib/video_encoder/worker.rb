# frozen_string_literal: true

module VideoEncoder
  # Worker processes encoding jobs from a repository.
  class Worker
    def initialize(repo:, encoder:, logger:)
      @repo = repo
      @encoder = encoder
      @logger = logger
    end

    def run_once
      processed = 0

      loop do
        job = @repo.next
        break unless job

        processed += 1
        log_start(job)
        process_job(job)
      end
      log('No queued jobs') if processed.zero?
    end

    def run
      log 'Worker started'

      loop do
        run_once
        sleep 1
      end
    rescue Interrupt
      log 'Stopping worker...'
    end

    private

    def log_start(job)
      log "Start job #{job.id}"
    end

    def process_job(job)
      @repo.mark_running(job)

      @encoder.encode(job)

      @repo.mark_done(job)

      log "Done job #{job.id}"
    rescue StandardError => e
      @repo.mark_failed(job, e.message)
      log "Failed job #{job.id}: #{e.message}"
    end

    def log(msg)
      @logger.info("[Worker] #{msg}")
    end
  end
end
