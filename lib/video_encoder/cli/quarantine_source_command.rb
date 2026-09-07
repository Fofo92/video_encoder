# frozen_string_literal: true

module VideoEncoder
  class CLI
    # Moves an explicitly confirmed source into quarantine.
    class QuarantineSourceCommand
      USAGE = 'Usage: video_encoder quarantine-source ' \
              '<source> --confirm'

      def self.build(argv:, repo:, config:)
        source_usage =
          ActiveTrimExportSourceUsage.new(
            repo: repo
          )

        check = SourceQuarantineCheck.new(
          source_usage: source_usage
        )

        quarantine = QuarantineSource.new(
          check: check,
          quarantine_directory:
            config.directories.quarantine
        )

        new(
          argv: argv,
          quarantine: quarantine
        )
      end

      def initialize(
        argv:,
        quarantine:,
        output: $stdout
      )
        @argv = argv
        @quarantine = quarantine
        @output = output
      end

      def run
        validate_arguments

        destination = quarantine.call(
          argv.first
        )

        output.puts(
          "Source moved to quarantine: #{destination}"
        )
      rescue QuarantineSource::Error => e
        abort(e.message)
      end

      private

      attr_reader :argv, :quarantine, :output

      def validate_arguments
        valid = argv.length == 2 &&
                argv.last == '--confirm'

        abort(USAGE) unless valid
      end
    end
  end
end
