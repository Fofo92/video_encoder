# frozen_string_literal: true

module VideoEncoder
  class CLI
    # Formats queued jobs for command-line output.
    class JobPresenter
      HEADER = 'ID | TYPE | INPUT | OUTPUT | STATUS'

      def summary(job)
        [
          job.id,
          job.kind,
          job.input_path,
          job.output_path || '-',
          job.status,
          "attempts=#{job.attempts}"
        ].join(' | ')
      end

      def details(job)
        [
          "ID:       #{job.id}",
          "Type:     #{job.kind}",
          "Input:    #{job.input_path}",
          "Output:   #{job.output_path || '-'}",
          "Status:   #{job.status}",
          "Attempts: #{job.attempts}",
          "Created:  #{job.created_at}",
          "Started:  #{job.started_at}",
          "Finished: #{job.finished_at}",
          "Error:    #{job.error}"
        ].join("\n")
      end

      def failure(job)
        "#{summary(job)} | error=#{job.error}"
      end
    end
  end
end
