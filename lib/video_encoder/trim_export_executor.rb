# frozen_string_literal: true

require 'fileutils'

module VideoEncoder
  # Executes one queued trim export in its own workspace.
  class TrimExportExecutor
    def initialize(
      service_factory:,
      file: File,
      filesystem: FileUtils
    )
      @service_factory = service_factory
      @file = file
      @filesystem = filesystem
    end

    def call(job)
      if file.exist?(job.output_path)
        raise ArgumentError,
              "output already exists: #{job.output_path}"
      end

      workspace_directory = TrimWorkspace.directory_for(
        job.output_path
      )

      filesystem.mkdir_p(workspace_directory)

      service_factory.build(
        workspace_directory: workspace_directory
      ).call(
        project_path: job.project_path.to_s,
        output_path: job.output_path.to_s
      )
    end

    private

    attr_reader :service_factory, :file, :filesystem
  end
end
