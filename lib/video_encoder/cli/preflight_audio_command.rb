# frozen_string_literal: true

module VideoEncoder
  class CLI
    # Checks a persisted project's audio tracks and prints a JSON report.
    class PreflightAudioCommand
      def initialize(argv:, dependency_checker:, service: nil, output: $stdout)
        @argv = argv
        @dependency_checker = dependency_checker
        @service = service
        @output = output
      end

      def run
        abort('Usage: video_encoder preflight-audio <project.json>') unless argv.length == 1

        dependency_checker.call('ffmpeg', 'ffprobe')

        results = service.call(project_path: argv.first)
        output.puts(AudioPreflightReport.new.call(results))
      end

      private

      attr_reader :argv, :dependency_checker, :output

      def service
        @service ||= CheckTrimProjectAudioFile.new(
          reader: File,
          loader: TrimProjectLoader.new(media_probe: MediaProbe.new),
          checker: CheckTrimProjectAudio.new(
            selector: TrackSelector.new,
            planner: TrackPreflightPlanner.new,
            checker: AudioPreflightChecker.new(
              analyzer: AudioSampleAnalyzer.new
            )
          )
        )
      end
    end
  end
end
