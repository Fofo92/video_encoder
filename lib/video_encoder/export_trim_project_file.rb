# frozen_string_literal: true

module VideoEncoder
  # Loads and exports a persisted trim project.
  class ExportTrimProjectFile
    def initialize(reader:, loader:, exporter:, receipt: nil)
      @reader = reader
      @loader = loader
      @exporter = exporter
      @receipt = receipt
    end

    def call(project_path:, output_path:)
      document = reader.read(project_path)
      project = loader.load(document)

      result = exporter.call(
        trim_project: project,
        output_path: output_path
      )
      @receipt&.call(project_path: project_path, project_json: document,
                     trim_project: project, output_path: output_path)
      result
    end

    private

    attr_reader :reader, :loader, :exporter
  end
end
