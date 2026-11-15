# frozen_string_literal: true

require 'json'

module VideoEncoder
  # Routes copied whole DVD titles through the validated subtitle-preserving path.
  class DvdProjectFileExport
    def initialize(fallback:, runner:, workspace_directory:, reader: File, receipt: ExportReceipt.new)
      @fallback = fallback
      @runner = runner
      @workspace_directory = workspace_directory
      @reader = reader
      @receipt = receipt
    end

    def call(project_path:, output_path:)
      json = @reader.read(project_path)
      document = JSON.parse(json)
      unless document['format'] == 'video_encoder.dvd_project'
        return @fallback.call(project_path: project_path, output_path: output_path)
      end

      script = File.expand_path('dvd_pipeline.py', __dir__)
      @runner.run('python3', script, 'export', project_path, output_path, @workspace_directory.to_s)
      roles = document.fetch('dvd').fetch('audio').map { |track| track.fetch('role') }
      @receipt.call(project_path: project_path, project_json: json, trim_project: nil,
                    output_path: output_path, audio_roles: roles)
    end
  end
end
