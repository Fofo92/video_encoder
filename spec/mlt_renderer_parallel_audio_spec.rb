# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::MltRenderer do
  let(:runner) { instance_double(VideoEncoder::CommandRunner) }
  let(:parallel_runner) { instance_double(VideoEncoder::ParallelCommandRunner) }
  let(:renderer) { described_class.new(runner: runner, parallel_runner: parallel_runner) }
  let(:inputs) do
    %w[french original].map do |role|
      { project_path: "tmp/audio_#{role}.mlt", output_path: "tmp/audio_#{role}.mka" }
    end
  end

  it 'uses separate audio projects, unchanged codecs, and diagnostic logs' do
    allow(parallel_runner).to receive(:run)
    allow(File).to receive(:file?).and_return(true)
    allow(File).to receive(:empty?).and_return(false)

    renderer.render_audio_batch(inputs)

    commands = inputs.map do |input|
      {
        argv: ['melt-7', '-progress2', input[:project_path], '-consumer',
               "avformat:#{input[:output_path]}", 'acodec=aac', 'ab=160k', 'vn=1'],
        log_path: "#{input[:output_path]}.log"
      }
    end
    expect(parallel_runner).to have_received(:run).with(commands, limit: 2)
  end

  it 'rejects a missing or empty output even if both processes exited successfully' do
    allow(parallel_runner).to receive(:run)
    allow(File).to receive(:file?).and_return(true)
    allow(File).to receive(:empty?).with('tmp/audio_french.mka').and_return(false)
    allow(File).to receive(:empty?).with('tmp/audio_original.mka').and_return(true)

    expect { renderer.render_audio_batch(inputs) }.to raise_error(described_class::RenderFailed)
  end
end
