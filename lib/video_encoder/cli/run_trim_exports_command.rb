# frozen_string_literal: true

require 'logger'

module VideoEncoder
  class CLI
    # Runs queued trim exports once or continuously.
    class RunTrimExportsCommand
      USAGE = 'Usage: video_encoder run-trim-exports ' \
              '[--once]'

      def initialize(
        argv:,
        repo:,
        dependency_checker:,
        command_probe:,
        worker: nil,
        logger: Logger.new($stdout)
      )
        @argv = argv
        @repo = repo
        @dependency_checker = dependency_checker
        @command_probe = command_probe
        @worker = worker
        @logger = logger
      end

      def run
        validate_arguments
        check_dependencies

        if argv == ['--once']
          worker.run_once
        else
          worker.run
        end
      end

      private

      attr_reader :argv,
                  :repo,
                  :dependency_checker,
                  :command_probe,
                  :logger

      def validate_arguments
        valid = argv.empty? ||
                argv == ['--once']

        abort(USAGE) unless valid
      end

      def check_dependencies
        dependency_checker.call(
          'ffmpeg',
          'ffprobe',
          'melt-7',
          ccextractor_executable
        )

        command_probe.call(
          ccextractor_executable,
          '--version'
        )
      end

      def worker
        @worker ||= TrimExportWorker.new(
          repo: repo,
          executor: executor,
          logger: logger
        )
      end

      def executor
        TrimExportExecutor.new(
          service_factory: service_factory
        )
      end

      def service_factory
        TrimProjectFileExportFactory.new(
          runner: CommandRunner.new,
          media_probe: MediaProbe.new,
          reader: File,
          ccextractor_executable:
            ccextractor_executable,
          synchronization_delay: 0,
          progress_reporter:
            ExportProgressReporter.new(
              output: $stdout
            )
        )
      end

      def ccextractor_executable
        ENV.fetch(
          'CCEXTRACTOR_EXECUTABLE',
          'ccextractor'
        )
      end
    end
  end
end
