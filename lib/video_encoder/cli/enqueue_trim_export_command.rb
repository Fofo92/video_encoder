# frozen_string_literal: true

module VideoEncoder
  class CLI
    # Enqueues the export of a prepared trim project.
    class EnqueueTrimExportCommand
      USAGE = 'Usage: video_encoder enqueue-trim-export ' \
              '<project.json> --output <movie.mkv>'

      def initialize(argv:, repo:, file: File)
        @argv = argv
        @repo = repo
        @file = file
      end

      def run
        project_path = argv.shift
        option = argv.shift
        output_path = argv.shift

        validate_arguments(
          project_path,
          option,
          output_path
        )

        validate_paths(
          project_path,
          output_path
        )

        job = TrimExportJob.new(
          project_path: project_path,
          output_path: output_path
        )

        repo.enqueue(job)

        puts(
          "Enqueued trim export: #{job.id} " \
          "(#{project_path} -> #{output_path})"
        )
      end

      private

      attr_reader :argv, :repo, :file

      def validate_arguments(
        project_path,
        option,
        output_path
      )
        valid = project_path &&
                option == '--output' &&
                output_path &&
                argv.empty?

        abort(USAGE) unless valid
      end

      def validate_paths(project_path, output_path)
        unless file.file?(project_path)
          abort(
            "project file not found: #{project_path}"
          )
        end

        return unless file.exist?(output_path)

        abort(
          "output already exists: #{output_path}"
        )
      end
    end
  end
end
