# frozen_string_literal: true

require 'json'

module VideoEncoder
  class CLI
    # Inspects one media source and writes a JSON report.
    class InspectMediaCommand
      FORMAT = 'video_encoder.media_inspection'
      VERSION = 1

      def initialize(
        argv:,
        dependency_checker:,
        media_probe: nil,
        serializer: MediaInspectionSerializer.new,
        output: $stdout
      )
        @argv = argv
        @dependency_checker = dependency_checker
        @media_probe = media_probe
        @serializer = serializer
        @output = output
      end

      def run
        unless argv.length == 1
          abort(
            'Usage: video_encoder inspect-media <file>'
          )
        end

        dependency_checker.call('ffprobe')

        media = media_probe.read(argv.first)

        output.puts(
          JSON.generate(
            format: FORMAT,
            version: VERSION,
            source: {
              path: media.path.to_s,
              inspection: serializer.call(media)
            }
          )
        )
      end

      private

      attr_reader :argv,
                  :dependency_checker,
                  :serializer,
                  :output

      def media_probe
        @media_probe ||= MediaProbe.new
      end
    end
  end
end
