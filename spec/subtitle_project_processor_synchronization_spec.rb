# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleProjectProcessor do
  it 'measures and applies one correction per subtitle segment' do
    extractor = instance_double(
      VideoEncoder::FfmpegSubtitleSegmentExtractor
    )

    concatenator = instance_double(
      VideoEncoder::FfmpegSubtitleProjectConcatenator
    )

    ocr = instance_double(
      VideoEncoder::CcextractorOcr
    )

    synchronization_probe = instance_double(
      VideoEncoder::SubtitleSegmentSynchronizationProbe
    )

    ocr_timing_correction = instance_double(
      VideoEncoder::SubtitleOcrTimingCorrection
    )

    timeline_normalizer = instance_double(
      VideoEncoder::SubtitleTimelineNormalizer
    )

    reader = instance_double('SrtReader')

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

    subtitle_track = instance_double(
      VideoEncoder::Track
    )

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
        alignment_offset: -0.48
      )
      .and_return(2.58)

    allow(synchronization_probe)
      .to receive(:call)
      .with(
        source_path: Pathname('/media/movie.m2t'),
        source_stream_index: 0,
        source_start_seconds: Rational(1_200, 1),
        duration_seconds: 60,
        transport_path: '/tmp/subtitle_segment_1.ts',
        rendered_video_path: '/tmp/video.mkv',
        rendered_start_seconds: 60
      )
      .and_return(
        offset_seconds: -0.48,
        confidence: 0.99
      )

    allow(timeline_normalizer)
      .to receive(:call)
      .with(
        "raw project srt\n",
        timeline_start: 60,
        segments: [
          {
            duration: Rational(60, 1),
            offset_seconds: 2.58
          }
        ]
      )
      .and_return("normalized project srt\n")

    processor = described_class.new(
      extractor: extractor,
      concatenator: concatenator,
      ocr: ocr,
      ocr_timing_correction: ocr_timing_correction,
      synchronization_probe: synchronization_probe,
      timeline_normalizer: timeline_normalizer,
      reader: reader,
      synchronization_delay: 0
    )

    result = processor.call(
      segments: [
        {
          segment: segment,
          video_track: video_track,
          subtitle_track: subtitle_track,
          transport_path:
            '/tmp/subtitle_segment_1.ts'
        }
      ],
      timeline_start: 60,
      rendered_video_path: '/tmp/video.mkv',
      manifest_path:
        '/tmp/subtitle_project_0.ffconcat',
      transport_path:
        '/tmp/subtitle_project_0.ts',
      srt_path:
        '/tmp/subtitle_project_0.srt'
    )

    expect(result).to eq(
      "normalized project srt\n"
    )
  end
end
