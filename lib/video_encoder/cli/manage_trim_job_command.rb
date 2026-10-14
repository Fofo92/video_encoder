# frozen_string_literal: true

module VideoEncoder
  class CLI
    # Changes inactive queue jobs while the repository guards worker races.
    class ManageTrimJobCommand
      def initialize(action:, argv:, repo:)
        @action = action
        @argv = argv
        @repo = repo
      end

      def run
        id = @argv.shift
        abort('job identifier is required') unless id

        changed = perform_action(id)
        abort('job no longer exists or is not eligible for this action') unless changed

        puts "#{@action}: #{id}"
      rescue Persistence::JobRepository::QueueActionError,
             ArgumentError, SystemCallError, JSON::ParserError => e
        abort(e.message)
      end

      private

      def perform_action(id)
        case @action
        when 'defer-job'
          validate_empty
          @repo.defer_queued?(id)
        when 'resume-job'
          validate_empty
          @repo.resume_deferred?(id)
        when 'set-job-output'
          change_output?(id)
        when 'delete-job'
          remove_job?(id)
        end
      end

      def change_output?(id)
        option = @argv.shift
        path = @argv.shift
        valid = option == '--output' && path && @argv.empty?
        abort('Usage: set-job-output ID --output movie.mkv') unless valid

        @repo.update_pending_output?(id, path)
      end

      def remove_job?(id)
        valid = @argv.empty? || @argv == ['--delete-project']
        abort('Usage: delete-job ID [--delete-project]') unless valid

        @repo.delete_inactive?(
          id,
          delete_project: @argv == ['--delete-project']
        )
      end

      def validate_empty
        abort("Usage: #{@action} ID") unless @argv.empty?
      end
    end
  end
end
