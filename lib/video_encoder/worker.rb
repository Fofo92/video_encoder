# frozen_string_literal: true

module VideoEncoder
  # Worker processes encoding jobs from a repository.
  class Worker
    def initialize(repo:, encoder:, verifier:, logger:, workspace:)
      @repo = repo
      @encoder = encoder
      @verifier = verifier
      @logger = logger
      @workspace = workspace
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

      output = nil
      encoding_job = nil

      source = @workspace.move_to_encoding(job.source)
      encoding_job = job.with_source(source)

      output = @encoder.encode(encoding_job)

      @verifier.verify!(output)

      @workspace.finalize(
        source: encoding_job.source,
        output: output
      )

      @repo.mark_done(encoding_job)

      log "Done job #{encoding_job.id}"
    rescue StandardError => e
      @workspace.remove_partial_output(output) if output

      @repo.mark_failed(encoding_job || job, e.message)

      log "Failed job #{(encoding_job || job).id}: #{e.message}"
    end
  end
end
