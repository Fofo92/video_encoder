# frozen_string_literal: true

require "fileutils"

module VideoEncoder
  class Workspace
    def initialize(directories:)
      @directories = directories
    end

    def move_to_encoding(source)
      move(source, @directories.encoding)
    end

    def move_to_encoded(output)
      move(output, @directories.encoded)
    end

    def move_to_archive(source)
      move(source, @directories.archive)
    end

    def finalize(source:, output:)
      output = move_to_encoded(output)
      move_to_archive(source)
      output
    end

    def remove_partial_output(output)
      FileUtils.rm_f(output) if output && File.exist?(output)
    end

    private

    def move(path, destination_dir)
      destination = File.join(destination_dir, File.basename(path))
      FileUtils.mv(path, destination)
      destination
    end
  end
end
