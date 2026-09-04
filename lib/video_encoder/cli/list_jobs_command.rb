# frozen_string_literal: true

require 'json'

module VideoEncoder
  class CLI
    # Lists queued jobs for humans or external consumers.
    class ListJobsCommand
      FORMAT = 'video_encoder.job_list'
      VERSION = 1

      def initialize(
        argv:,
        repo:,
        presenter: JobPresenter.new,
        serializer: JobSerializer.new,
        output: $stdout
      )
        @argv = argv
        @repo = repo
        @presenter = presenter
        @serializer = serializer
        @output = output
      end

      def run
        validate_arguments

        if json?
          write_json
        else
          write_text
        end
      end

      private

      attr_reader :argv,
                  :repo,
                  :presenter,
                  :serializer,
                  :output

      def validate_arguments
        return if argv.empty? || argv == ['--json']

        abort('Usage: video_encoder list [--json]')
      end

      def json?
        argv == ['--json']
      end

      def write_json
        output.puts(
          JSON.generate(
            format: FORMAT,
            version: VERSION,
            jobs: repo.all.map do |job|
              serializer.call(job)
            end
          )
        )
      end

      def write_text
        jobs = repo.all

        output.puts(JobPresenter::HEADER)
        output.puts('-' * 80)

        if jobs.empty?
          output.puts('No jobs found')
          return
        end

        jobs.each do |job|
          output.puts(presenter.summary(job))
        end
      end
    end
  end
end
