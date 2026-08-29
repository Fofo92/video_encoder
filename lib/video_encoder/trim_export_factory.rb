# frozen_string_literal: true

module VideoEncoder
  # Builds the complete trim export application service.
  class TrimExportFactory
    def initialize(
      runner:,
      ccextractor_executable:,
      synchronization_delay:,
      progress_reporter: nil
    )
      @runner = runner
      @ccextractor_executable = ccextractor_executable
      @synchronization_delay = synchronization_delay
      @progress_reporter = progress_reporter
    end

    def build(workspace_directory:)
      workspace = TrimWorkspace.new(
        directory: workspace_directory
      )

      trim_exporter = TrimExporter.new(
        builder: MltProjectBuilder.new,
        renderer: MltRenderer.new(runner: runner),
        remuxer: FfmpegRemuxer.new(runner: runner),
        workspace: workspace,
        subtitle_exporter: build_subtitle_exporter(workspace),
        progress_reporter: progress_reporter
      )

      exporter = WorkspaceCleaningExporter.new(
        exporter: trim_exporter,
        workspace: workspace
      )

      ExportTrimProject.new(
        selector: TrackSelector.new,
        exporter: exporter
      )
    end

    private

    attr_reader :runner,
                :ccextractor_executable,
                :synchronization_delay,
                :progress_reporter

    def build_subtitle_exporter(workspace)
      processor = SubtitleProjectProcessor.new(
        extractor: FfmpegSubtitleSegmentExtractor.new(
          runner: runner
        ),
        concatenator: FfmpegSubtitleProjectConcatenator.new(
          runner: runner,
          writer: File
        ),
        ocr: CcextractorOcr.new(
          runner: runner,
          executable: ccextractor_executable
        ),
        normalizer: SrtNormalizer.new,
        reader: File,
        synchronization_delay: synchronization_delay
      )

      TrimSubtitleExporter.new(
        processor: processor,
        composer: SrtComposer.new,
        workspace: workspace
      )
    end
  end
end
