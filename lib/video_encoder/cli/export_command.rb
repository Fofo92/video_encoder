# frozen_string_literal: true

require 'fileutils'

module VideoEncoder
  class CLI
    # Exports a persisted trim project from command-line arguments.
    class ExportCommand
      def initialize(argv:, dependency_checker:, command_probe:, service: nil)
        @argv = argv
        @service = service
        @dependency_checker = dependency_checker
        @command_probe = command_probe
      end

      def run
        project_path = argv.shift
        option = argv.shift
        output_path = argv.shift

        validate_arguments(project_path, option, output_path)
        check_dependencies

        service_for(output_path).call(
          project_path: project_path,
          output_path: output_path
        )
      end

      private

      attr_reader :argv, :dependency_checker, :command_probe

      def validate_arguments(project_path, option, output_path)
        return if project_path && option == '--output' && output_path

        abort(
          'Usage: video_encoder export ' \
          '<project.json> --output <movie.mkv>'
        )
      end

      def service_for(output_path)
        return @service if @service

        workspace_directory = workspace_directory_for(output_path)
        FileUtils.mkdir_p(workspace_directory)

        @service = TrimProjectFileExportFactory.new(
          runner: CommandRunner.new,
          media_probe: MediaProbe.new,
          reader: File,
          ccextractor_executable: ccextractor_executable,
          synchronization_delay: 0,
          progress_reporter: ExportProgressReporter.new(
            output: $stdout
          )
        ).build(
          workspace_directory: workspace_directory
        )
      end

      def workspace_directory_for(output_path)
        expanded_output = File.expand_path(output_path)
        basename = File.basename(
          expanded_output,
          File.extname(expanded_output)
        )

        File.join(
          File.dirname(expanded_output),
          "video_encoder_#{basename}_workspace"
        )
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

      def ccextractor_executable
        ENV.fetch('CCEXTRACTOR_EXECUTABLE', 'ccextractor')
      end
    end
  end
end
