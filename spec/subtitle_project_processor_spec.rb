# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleProjectProcessor do
  subject(:processor) do
    described_class.new(
      extractor: extractor,
      concatenator: concatenator,
      ocr: ocr,
      ocr_timing_correction:
        ocr_timing_correction,
      synchronization_probe:
        synchronization_probe,
      timeline_normalizer:
        timeline_normalizer,
      reader: reader,
      synchronization_delay: 0
    )
  end

  let(:ocr_timing_correction) do
    instance_double(
      VideoEncoder::SubtitleOcrTimingCorrection
    )
  end

  let(:extractor) do
    instance_double(VideoEncoder::FfmpegSubtitleSegmentExtractor)
  end

  let(:concatenator) do
    instance_double(VideoEncoder::FfmpegSubtitleProjectConcatenator)
  end

  let(:ocr) { instance_double(VideoEncoder::CcextractorOcr) }

  let(:synchronization_probe) do
    instance_double(
      VideoEncoder::SubtitleSegmentSynchronizationProbe
    )
  end

  let(:timeline_normalizer) do
    instance_double(
      VideoEncoder::SubtitleTimelineNormalizer
    )
  end
  let(:reader) { instance_double('SrtReader') }

  describe '#call' do
    it 'extracts and OCRs one continuous subtitle project' do
      media = instance_double(
        VideoEncoder::Media,
        path: Pathname('/media/movie.m2t')
      )

      segment = instance_double(
        VideoEncoder::Segment,
        source: media,
        start_frame: 30_000,
        end_frame: 31_499
      )

      video_track = instance_double(
        VideoEncoder::VideoTrack,
        index: 0,
        frame_rate: Rational(25, 1)
      )

      subtitle_track = instance_double(VideoEncoder::Track)

      allow(extractor).to receive(:call)
      allow(concatenator).to receive(:call)
      allow(ocr).to receive(:call)

      allow(reader)
        .to receive(:read)
        .with('/tmp/subtitle_project_0.srt')
        .and_return("raw project srt\n")

      allow(ocr_timing_correction)
        .to receive(:call)
        .with(
          srt: "raw project srt\n",
          transport_path:
            '/tmp/subtitle_project_0.ts',
          alignment_offset: 0
        )
        .and_return(0)

      allow(synchronization_probe)
        .to receive(:call)
        .and_return(
          offset_seconds: 0,
          confidence: 1.0
        )

      allow(timeline_normalizer)
        .to receive(:call)
        .with(
          "raw project srt\n",
          timeline_start: 60,
          segments: [
            {
              duration: Rational(60, 1),
              offset_seconds: 0
            }
          ]
        )
        .and_return(
          "normalized project srt\n"
        )

      result = processor.call(
        segments: [
          {
            segment: segment,
            video_track: video_track,
            subtitle_track: subtitle_track,
            transport_path: '/tmp/subtitle_segment_1.ts'
          }
        ],
        timeline_start: 60,
        rendered_video_path: '/tmp/video.mkv',
        manifest_path: '/tmp/subtitle_project_0.ffconcat',
        transport_path: '/tmp/subtitle_project_0.ts',
        srt_path: '/tmp/subtitle_project_0.srt'
      )

      expect(extractor).to have_received(:call).with(
        source_path: Pathname('/media/movie.m2t'),
        video_track: video_track,
        subtitle_track: subtitle_track,
        start_time: Rational(1_200, 1),
        duration: Rational(60, 1),
        output_path: '/tmp/subtitle_segment_1.ts'
      )

      expect(concatenator).to have_received(:call).with(
        segments: [
          {
            path: '/tmp/subtitle_segment_1.ts',
            duration: Rational(60, 1)
          }
        ],
        manifest_path: '/tmp/subtitle_project_0.ffconcat',
        output_path: '/tmp/subtitle_project_0.ts'
      )

      expect(ocr).to have_received(:call).with(
        input_path: '/tmp/subtitle_project_0.ts',
        output_path: '/tmp/subtitle_project_0.srt'
      )

      expect(result).to eq("normalized project srt\n")
    end
  end
end
