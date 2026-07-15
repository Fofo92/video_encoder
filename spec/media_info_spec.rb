# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::MediaInfo do
  subject(:media_info) { described_class.new }

  describe '#duration' do
    it 'returns the duration in seconds' do
      status = instance_double(Process::Status, success?: true)

      allow(Open3)
        .to receive(:capture3)
        .and_return(["123.456\n", "", status])

      expect(
        media_info.duration('movie.m2t')
      ).to eq(123.456)
    end

    it 'raises when ffprobe fails' do
      status = instance_double(
        Process::Status,
        success?: false,
        exitstatus: 1
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return(["", "file not found\n", status])

      expect {
        media_info.duration('movie.m2t')
      }.to raise_error(RuntimeError, /file not found/)
    end
  end
end
