# frozen_string_literal: true

module VideoEncoder
  # Loads and exports a persisted trim project.
  class ExportTrimProjectFile
    def initialize(reader:, loader:, exporter:, receipt: nil, timings: nil)
      @reader = reader
      @loader = loader
      @exporter = exporter
      @receipt = receipt
      @timings = timings
    end

    def call(project_path:, output_path:)
      document = reader.read(project_path)
      project = loader.load(document)

      result = exporter.call(
        trim_project: project,
        output_path: output_path
      )
      receipt_arguments = { project_path: project_path, project_json: document,
                            trim_project: project, output_path: output_path }
      receipt_arguments[:timings] = @timings.entries if @timings
      @receipt&.call(**receipt_arguments)
      result
    end

    private

    attr_reader :reader, :loader, :exporter
  end
end
