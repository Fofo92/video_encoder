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
        '--codec', 'dvbsub',
        '--streamtype', '6',
        '--ocrlang', 'fra',
        '--ocr-line-split',
        '--out', 'srt',
        '/tmp/subtitle_segment.ts',
        '-o', '/tmp/subtitle_segment.srt'
      )
    end
  end
end
