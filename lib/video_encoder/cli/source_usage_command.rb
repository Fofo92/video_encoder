# frozen_string_literal: true

require 'json'

module VideoEncoder
  class CLI
    # Reports queued and running exports using a source.
    class SourceUsageCommand
      FORMAT = 'video_encoder.source_usage'
      VERSION = 1
      USAGE = 'Usage: video_encoder source-usage <source>'

      def self.build(argv:, repo:)
        new(
          argv: argv,
          source_usage:
            ActiveTrimExportSourceUsage.new(
              repo: repo
            )
        )
      end

      def initialize(
        argv:,
        source_usage:,
        serializer: JobSerializer.new,
        output: $stdout
      )
        @argv = argv
        @source_usage = source_usage
        @serializer = serializer
        @output = output
      end

      def run
        abort(USAGE) unless argv.length == 1

        source = argv.first
        jobs = source_usage.call(source)

        output.puts(
          JSON.generate(
            format: FORMAT,
            version: VERSION,
            source: source,
            active_jobs: jobs.map do |job|
              serializer.call(job)
            end
          )
        )
      end

      private

      attr_reader :argv,
                  :source_usage,
                  :serializer,
                  :output
    end
  end
end
