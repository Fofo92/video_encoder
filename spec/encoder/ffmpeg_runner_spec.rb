# frozen_string_literal: true

require 'spec_helper'
require 'stringio'

RSpec.describe VideoEncoder::Encoder::FFmpegRunner do
  let(:logger) do
    instance_double(Logger, info: nil, error: nil)
  end

  subject(:runner) do
    described_class.new(logger: logger)
  end

  describe '#run' do
    let(:success) do
      instance_double(Process::Status, success?: true)
    end

    let(:failure) do
      instance_double(
        Process::Status,
        success?: false,
        exitstatus: 1
      )
    end

    it 'runs the command successfully' do
      allow(Open3).to receive(:popen3).and_yield(
        nil,
        StringIO.new(""),
        StringIO.new(""),
        instance_double(Thread, value: success)
      )

      expect {
        runner.run(%w[ffmpeg -version])
      }.not_to raise_error

      expect(Open3)
        .to have_received(:popen3)
        .with("ffmpeg", "-version")
    end

    it 'raises when the command fails' do
      allow(Open3).to receive(:popen3).and_yield(
        nil,
        StringIO.new(""),
        StringIO.new("input file not found\n"),
        instance_double(Thread, value: failure)
      )

      expect {
        runner.run(%w[ffmpeg -i input.m2t])
      }.to raise_error(
        RuntimeError,
        /input file not found/
      )
    end

    it "yields output lines" do
      received = []

      allow(Open3).to receive(:popen3).and_yield(
        nil,
        StringIO.new("line1\nline2\n"),
        StringIO.new("warning\n"),
        instance_double(Thread, value: success)
      )

      runner.run(%w[ffmpeg -version]) do |stream, line|
        received << [stream, line]
      end

      expect(received).to contain_exactly(
        [:stdout, "line1\n"],
        [:stdout, "line2\n"],
        [:stderr, "warning\n"]
      )
    end
  end
end
