# frozen_string_literal: true

module VideoEncoder
  # Builds the service that loads and exports a persisted trim project.
  class TrimProjectFileExportFactory
    def initialize(
      runner:,
      media_probe:,
      reader:,
      ccextractor_executable:,
      synchronization_delay:,
      progress_reporter: nil
    )
      @runner = runner
      @media_probe = media_probe
      @reader = reader
      @ccextractor_executable = ccextractor_executable
      @synchronization_delay = synchronization_delay
      @progress_reporter = progress_reporter
    end

    def build(workspace_directory:)
      exporter = TrimExportFactory.new(
        runner: runner,
        ccextractor_executable: ccextractor_executable,
        synchronization_delay: synchronization_delay,
        progress_reporter: progress_reporter
      ).build(
        workspace_directory: workspace_directory
      )

      ExportTrimProjectFile.new(
        reader: reader,
        loader: TrimProjectLoader.new(media_probe: media_probe),
        exporter: exporter
      )
    end

    private

    attr_reader :runner,
                :media_probe,
                :reader,
                :ccextractor_executable,
                :synchronization_delay,
                :progress_reporter
  end
end
