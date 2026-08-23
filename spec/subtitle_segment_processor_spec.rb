# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleSegmentProcessor do
  subject(:processor) do
    described_class.new(
      extractor: extractor,
      ocr: ocr,
      normalizer: normalizer,
      reader: reader,
      synchronization_delay: 0.65
    )
  end

  let(:extractor) do
    instance_double(VideoEncoder::FfmpegSubtitleSegmentExtractor)
  end

  let(:ocr) { instance_double(VideoEncoder::CcextractorOcr) }
  let(:normalizer) { instance_double(VideoEncoder::SrtNormalizer) }
  let(:reader) { instance_double('SrtReader') }

  describe '#call' do
    it 'extracts and normalizes one subtitle segment' do
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
        VideoEncoder::Track,
        index: 5
      )

      allow(extractor).to receive(:call)
      allow(ocr).to receive(:call)
      allow(reader).to receive(:read)
        .with('/tmp/segment.srt')
        .and_return("raw srt\n")

      allow(normalizer).to receive(:call)
        .with(
          "raw srt\n",
          offset: 60.65,
          end_at: 120
        )
        .and_return("normalized srt\n")

      result = processor.call(
        segment: segment,
        video_track: video_track,
        subtitle_track: subtitle_track,
        timeline_start: 60,
        transport_path: '/tmp/segment.ts',
        srt_path: '/tmp/segment.srt'
      )

      expect(extractor).to have_received(:call).with(
        source_path: Pathname('/media/movie.m2t'),
        video_track: video_track,
        subtitle_track: subtitle_track,
        start_time: Rational(1_200, 1),
        duration: Rational(60, 1),
        output_path: '/tmp/segment.ts'
      )

      expect(ocr).to have_received(:call).with(
        input_path: '/tmp/segment.ts',
        output_path: '/tmp/segment.srt'
      )

      expect(result).to eq("normalized srt\n")
    end
  end
end
