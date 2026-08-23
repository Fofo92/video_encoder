# frozen_string_literal: true

module VideoEncoder
  # Builds the complete trim export application service.
  class TrimExportFactory
    def initialize(
      runner:,
      ccextractor_executable:,
      synchronization_delay:
    )
      @runner = runner
      @ccextractor_executable = ccextractor_executable
      @synchronization_delay = synchronization_delay
    end

    def build(workspace_directory:)
      workspace = TrimWorkspace.new(
        directory: workspace_directory
      )

      exporter = TrimExporter.new(
        builder: MltProjectBuilder.new,
        renderer: MltRenderer.new(runner: runner),
        remuxer: FfmpegRemuxer.new(runner: runner),
        workspace: workspace,
        subtitle_exporter: build_subtitle_exporter(workspace)
      )

      ExportTrimProject.new(
        selector: TrackSelector.new,
        exporter: exporter
      )
    end

    private

    attr_reader :runner,
                :ccextractor_executable,
                :synchronization_delay

    def build_subtitle_exporter(workspace)
      processor = SubtitleSegmentProcessor.new(
        extractor: FfmpegSubtitleSegmentExtractor.new(
          runner: runner
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
