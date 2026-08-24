# frozen_string_literal: true

module VideoEncoder
  # Cleans a trim workspace after a successful export.
  class WorkspaceCleaningExporter
    def initialize(exporter:, workspace:)
      @exporter = exporter
      @workspace = workspace
    end

    def call(**arguments)
      result = exporter.call(**arguments)

      workspace.cleanup
      result
    end

    private

    attr_reader :exporter, :workspace
  end
end
