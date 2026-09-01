# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CcextractorOcr do
  subject(:ocr) { described_class.new(runner: runner) }

  let(:runner) { instance_double('CommandRunner') }

  describe '#call' do
    it 'converts DVB subtitles to French SRT' do
      allow(runner).to receive(:run)

      ocr.call(
        input_path: '/tmp/subtitle_segment.ts',
        output_path: '/tmp/subtitle_segment.srt'
      )

      expect(runner).to have_received(:run).with(
        'ccextractor',
        '--ts',
        '--codec', 'dvbsub',
        '--streamtype', '6',
        '--ocrlang', 'fra',
        '--ocr-line-split',
        '--ignoreptsjumps',
        '--out', 'srt',
        '/tmp/subtitle_segment.ts',
        '-o', '/tmp/subtitle_segment.srt'
      )
    end
    it 'reports when CCExtractor finds no subtitles' do
      status = instance_double(
        Process::Status,
        exitstatus: 10,
        termsig: nil,
        to_s: 'exit 10'
      )

      failure = VideoEncoder::CommandRunner::CommandFailed.new(
        command: ['ccextractor'],
        status: status
      )

      allow(runner).to receive(:run).and_raise(failure)

      expect do
        ocr.call(
          input_path: '/tmp/subtitle_segment.ts',
          output_path: '/tmp/subtitle_segment.srt'
        )
      end.to raise_error(
        VideoEncoder::CcextractorOcr::NoSubtitlesFound
      )
    end

    it 'identifies technical failures from CCExtractor' do
      status = instance_double(
        Process::Status,
        exitstatus: 2,
        termsig: nil,
        to_s: 'exit 2'
      )

      failure = VideoEncoder::CommandRunner::CommandFailed.new(
        command: ['ccextractor'],
        status: status
      )

      allow(runner).to receive(:run).and_raise(failure)

      expect do
        ocr.call(
          input_path: '/tmp/subtitle_segment.ts',
          output_path: '/tmp/subtitle_segment.srt'
        )
      end.to raise_error(
        VideoEncoder::CcextractorOcr::TechnicalFailure
      ) { |error|
        expect(error.failure).to equal(failure)
      }
    end
  end
end
