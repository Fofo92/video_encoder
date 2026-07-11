# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Verifier do
  let(:logger) { instance_double(Logger, info: nil, error: nil) }

  subject(:verifier) do
    described_class.new(logger: logger)
  end

  describe '#verify!' do
    let(:file) { 'encoded/video.mkv' }

    it 'returns true when ffprobe succeeds' do
      success = instance_double(Process::Status, success?: true)

      allow(Open3)
        .to receive(:capture3)
        .and_return(['', '', success])

      expect(verifier.verify!(file)).to be true
    end

    it 'raises when ffprobe fails' do
      failure = instance_double(
        Process::Status,
        success?: false,
        exitstatus: 1
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return(['', 'invalid file', failure])

      expect {
        verifier.verify!(file)
      }.to raise_error(RuntimeError, /invalid file/)
    end
  end
end
