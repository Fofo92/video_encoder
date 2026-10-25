# frozen_string_literal: true

module VideoEncoder
  # Processes queued trim export jobs.
  class TrimExportWorker
    def initialize(
      repo:,
      executor:,
      logger:,
      stop_requested: -> { false }
    )
      @repo = repo
      @executor = executor
      @logger = logger
      @stop_requested = stop_requested
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
        break if stop_requested.call
      end

      log('No queued trim exports') if processed.zero?
    end

    def run_selected(job_id)
      job = repo.find(job_id)
      raise ArgumentError, 'La tâche sélectionnée doit être en attente' unless job && job.status == Status::QUEUED

      return if process_job(job)

      raise ArgumentError, 'La tâche sélectionnée a échoué ou n’est plus disponible ; la file reste arrêtée'
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

    attr_reader :repo,
                :executor,
                :logger,
                :stop_requested

    def process_job(job)
      return unless repo.mark_running(job)

      job = repo.find(job.id)
      log("Start trim export #{job.id}")

      executor.call(job)

      repo.mark_done(job)
      log("Done trim export #{job.id}")
      true
    rescue Interrupt
      repo.mark_interrupted(
        job,
        'trim export interrupted'
      )
      log("Interrupted trim export #{job.id}")
      raise
    rescue StandardError => e
      repo.mark_failed(job, e.message)
      log(
        "Failed trim export #{job.id}: " \
        "#{e.message}"
      )
      false
    end

    def log(message)
      logger.info(
        "[TrimExportWorker] #{message}"
      )
    end
  end
end
