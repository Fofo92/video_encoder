# frozen_string_literal: true

module VideoEncoder
  # Shares the normal queue and receipt, preserving the source video/audio bitstreams.
  class CopyVersionFileExport < DvdProjectFileExport
    def call(project_path:, output_path:)
      json = @reader.read(project_path)
      return super unless JSON.parse(json)['format'] == 'video_encoder.copy_version'

      script = File.expand_path('copy_version_pipeline.py', __dir__)
      @runner.run('python3', script, 'export', project_path, output_path, @workspace_directory.to_s)
      @receipt.call(project_path: project_path, project_json: json, trim_project: nil,
                    output_path: output_path, audio_roles: ['original'])
    end
  end
end
