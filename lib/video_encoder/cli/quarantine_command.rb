# frozen_string_literal: true

require_relative '../quarantine_policy'

module VideoEncoder
  class CLI
    # JSON output is shared by the desktop view and the maintenance timer.
    class QuarantineCommand
      USAGE = 'Usage: video_encoder quarantine [list | enroll FILE [--project JSON] | sweep [--apply]]'

      def initialize(argv:, database:, root:, output: $stdout)
        @argv = argv
        @policy = QuarantinePolicy.new(database: database, root: root)
        @output = output
      end

      def run
        result = case @argv
                 when [], ['list'] then @policy.list
                 when ['sweep'] then @policy.sweep
                 when ['sweep', '--apply'] then @policy.sweep(apply: true)
                 else
                   enroll
                 end
        @output.puts(JSON.pretty_generate(result))
      rescue StandardError => e
        abort(e.message)
      end

      private

      def enroll
        valid = @argv.first == 'enroll' &&
                (@argv.size == 2 || (@argv.size == 4 && @argv[2] == '--project'))
        abort(USAGE) unless valid

        @policy.enroll(@argv[1], project: @argv[3])
      end
    end
  end
end
