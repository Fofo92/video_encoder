# frozen_string_literal: true

module VideoEncoder
  # Executes external commands without invoking a shell.
  class CommandRunner
    def initialize(executor: Kernel, logger: nil)
      @executor = executor
      @logger = logger
    end

    def run(*command)
      logger&.info(command.join(' '))

      executor.system(*command, exception: true)
    end

    private

    attr_reader :executor, :logger
  end
end
