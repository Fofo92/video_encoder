# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleProjectProcessor do
  subject(:processor) do
    described_class.new(
      extractor: extractor,
      concatenator: concatenator,
      ocr: ocr,
      normalizer: normalizer,
      reader: reader,
      synchronization_delay: 0
    )
  end

  let(:extractor) do
    instance_double(VideoEncoder::FfmpegSubtitleSegmentExtractor)
  end

  let(:concatenator) do
    instance_double(VideoEncoder::FfmpegSubtitleProjectConcatenator)
  end

  let(:ocr) { instance_double(VideoEncoder::CcextractorOcr) }
  let(:normalizer) { instance_double(VideoEncoder::SrtNormalizer) }
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

      allow(normalizer)
        .to receive(:call)
        .with(
          "raw project srt\n",
          offset: 60,
          start_at: 60,
          end_at: 120
        )
        .and_return("normalized project srt\n")

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
