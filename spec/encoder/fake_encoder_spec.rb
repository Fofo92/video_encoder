# frozen_string_literal: true

require 'spec_helper'
RSpec.describe VideoEncoder::Encoder::FakeEncoder do
  subject(:encoder) { described_class.new(logger: logger) }

  let(:logger) { instance_double(Logger, info: nil) }
  let(:job) { VideoEncoder::Job.new(source: 'video.mp4') }

  describe '#encode' do
    before do
      allow(encoder).to receive(:sleep)
    end
    it 'does not raise an exception for a valid file' do
      expect { encoder.encode(job) }.not_to raise_error
    end

    it 'logs each encoding step' do
      encoder.encode(job)

      expect(logger).to have_received(:info)
        .with('[FakeEncoder] video.mp4 1/3')

      expect(logger).to have_received(:info)
        .with('[FakeEncoder] video.mp4 2/3')

      expect(logger).to have_received(:info)
        .with('[FakeEncoder] video.mp4 3/3')
    end

    context "when the source contains 'fail'" do
      let(:job) { VideoEncoder::Job.new(source: 'fail_video.mp4') }

      it 'raises an exception' do
        expect { encoder.encode(job) }
          .to raise_error(RuntimeError, 'Simulated encoder failure')
      end
    end
  end
end
