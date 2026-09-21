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
        ocr_timing_correction:
          SubtitleOcrTimingCorrection.new(
            timing_probe:
              SubtitleTransportTimingProbe.new,
            tolerance_seconds: 0.08
          ),
        synchronization_probe:
          build_subtitle_synchronization_probe,
        timeline_normalizer:
          build_subtitle_timeline_normalizer,
        reader: SubtitleTextReader.new,
        synchronization_delay: synchronization_delay
      )

      TrimSubtitleExporter.new(
        processor: processor,
        composer: SrtComposer.new,
        workspace: workspace
      )
    end

    def build_subtitle_synchronization_probe
      SubtitleSegmentSynchronizationProbe.new(
        timeline_probe: VideoTimelineOffsetProbe.new(
          extractor: build_video_frame_sequence_extractor,
          correlator: VideoTimelineCorrelator.new(
            frame_rate: 25,
            maximum_shift_seconds: 3.0
          ),
          sample_duration_seconds: 12.0
        ),
        correction: SubtitleSynchronizationCorrection.new(
          minimum_confidence: 0.95
        ),
        sample_offsets_seconds: [
          0,
          15,
          30,
          60,
          120
        ],
        sample_duration_seconds: 12
      )
    end

    def build_video_frame_sequence_extractor
      VideoFrameSequenceExtractor.new(
        width: 32,
        height: 18,
        frame_rate: 25,
        seek_preroll_seconds: 5.0
      )
    end

    def build_subtitle_timeline_normalizer
      SubtitleTimelineNormalizer.new(
        normalizer: SrtNormalizer.new,
        composer: SrtComposer.new
      )
    end
  end
end
