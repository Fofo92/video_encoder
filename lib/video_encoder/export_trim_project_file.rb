# frozen_string_literal: true

module VideoEncoder
  # Loads and exports a persisted trim project.
  class ExportTrimProjectFile
    def initialize(reader:, loader:, exporter:)
      @reader = reader
      @loader = loader
      @exporter = exporter
    end

    def call(project_path:, output_path:)
      project = loader.load(reader.read(project_path))

      exporter.call(
        trim_project: project,
        output_path: output_path
      )
    end

    private

    attr_reader :reader, :loader, :exporter
  end
end
