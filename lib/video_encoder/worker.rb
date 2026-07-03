# frozen_string_literal: true

module VideoEncoder
  # Worker that processes video encoding jobs from a repository.
  class Worker
    def initialize(repo:, logger: STDOUT)
      @repo = repo
      @logger = logger
    end

    def run_once
      job = @repo.next
      return unless job

      log "Start job #{job.id} (#{job.source})"

      job.start!
      simulate_encoding(job)

      job.finish!

      log "Done job #{job.id}"
    rescue StandardError => e
      job&.fail!(e.message)
      log "Failed job #{job&.id}: #{e.message}"
    end

    def run_forever(interval: 2)
      loop do
        run_once
        sleep interval
      end
    end

    private

    def simulate_encoding(job)
      # simulation simple (plus tard ffmpeg ici)
      3.times do |i|
        log "Encoding #{job.id}: step #{i + 1}/3"
        sleep 1
      end
    end

    def log(msg)
      @logger.puts("[Worker] #{msg}")
    end
  end
end
