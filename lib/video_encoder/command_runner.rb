# frozen_string_literal: true

module VideoEncoder
  # Executes external commands without invoking a shell.
  class CommandRunner
    # Reports a command failure with its process status.
    class CommandFailed < StandardError
      attr_reader :exit_status, :term_signal

      def initialize(command:, status:)
        @exit_status = status&.exitstatus
        @term_signal = status&.termsig

        detail = status ? status.to_s : 'could not start'

        super("command failed: #{command.join(' ')} (#{detail})")
      end
    end

    def initialize(executor: Kernel, logger: nil)
      @executor = executor
      @logger = logger
    end

    def run(*command)
      logger&.info(command.join(' '))

      result = executor.system(*command, exception: false)
      return true if result

      status = result == false ? Process.last_status : nil

      raise CommandFailed.new(
        command: command,
        status: status
      )
    end

    private

    attr_reader :executor, :logger
  end
end
