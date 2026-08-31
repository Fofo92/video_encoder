# frozen_string_literal: true

module VideoEncoder
  # Loads a persisted trim project and checks its audio tracks.
  class CheckTrimProjectAudioFile
    def initialize(reader:, loader:, checker:)
      @reader = reader
      @loader = loader
      @checker = checker
    end

    def call(project_path:)
      project = loader.load(reader.read(project_path))

      checker.call(trim_project: project)
    end

    private

    attr_reader :reader, :loader, :checker
  end
end
