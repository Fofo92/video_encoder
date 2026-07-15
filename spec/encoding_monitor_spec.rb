# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::EncodingMonitor do
  let(:parser)   { instance_double(VideoEncoder::ProgressParser) }
  let(:progress) { instance_double(VideoEncoder::EncodingProgress) }
  let(:reporter) { instance_double(VideoEncoder::ProgressReporter) }

  subject(:monitor) do
    described_class.new(
      parser: parser,
      progress: progress,
      reporter: reporter
    )
  end

  describe '#call' do
    it 'updates the reporter when progress is parsed' do
      allow(parser)
        .to receive(:parse)
        .with('out_time_ms=12500000')
        .and_return(12.5)

      allow(progress)
        .to receive(:percent)
        .with(12.5)
        .and_return(42)

      allow(reporter)
        .to receive(:update)

      monitor.call(:stderr, 'out_time_ms=12500000')

      expect(reporter)
        .to have_received(:update)
        .with(42)
    end

    it 'ignores unrelated lines' do
      allow(parser)
        .to receive(:parse)
        .and_return(nil)

      allow(reporter)
        .to receive(:update)

      monitor.call(:stderr, 'frame=123')

      expect(reporter)
        .not_to have_received(:update)
    end
  end

  describe '#finish' do
    it 'delegates to the reporter' do
      allow(reporter).to receive(:finish)

      monitor.finish

      expect(reporter)
        .to have_received(:finish)
    end
  end
end
