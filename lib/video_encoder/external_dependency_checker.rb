# frozen_string_literal: true

require 'pathname'

module VideoEncoder
  class MissingExternalDependenciesError < StandardError; end

  # Verifies that required external commands are executable.
  class ExternalDependencyChecker
    def initialize(path: ENV.fetch('PATH', ''))
      @directories = path.split(File::PATH_SEPARATOR)
    end

    def call(*executables)
      missing = executables.reject { |executable| available?(executable) }

      return if missing.empty?

      raise MissingExternalDependenciesError, "missing external dependencies: #{missing.join(', ')}"
    end

    private

    attr_reader :directories

    def available?(executable)
      return executable_file?(executable) if Pathname.new(executable).absolute?

      directories.any? do |directory|
        executable_file?(File.join(directory, executable))
      end
    end

    def executable_file?(path)
      File.file?(path) && File.executable?(path)
    end
  end
end
