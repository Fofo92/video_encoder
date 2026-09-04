# frozen_string_literal: true

require 'time'

module VideoEncoder
  class CLI
    # Serializes jobs for external consumers.
    class JobSerializer
      def call(job)
        {
          id: job.id,
          kind: job.kind,
          input_path: job.input_path.to_s,
          output_path: serialize_path(job.output_path),
          status: job.status,
          attempts: job.attempts,
          created_at: serialize_time(job.created_at),
          started_at: serialize_time(job.started_at),
          finished_at: serialize_time(job.finished_at),
          error: job.error
        }
      end

      private

      def serialize_path(path)
        path&.to_s
      end

      def serialize_time(time)
        time&.iso8601
      end
    end
  end
end
