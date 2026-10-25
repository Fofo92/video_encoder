# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ExportTimings do
  it 'records monotonic wall time and audio settings while preserving the result' do
    clock = double('Clock')
    allow(clock).to receive(:call).and_return(100.0, 103.125)
    timings = described_class.new(clock: clock)

    expect(timings.measure(:audio, concurrency: 2) { :result }).to eq(:result)
    expect(timings.entries).to eq(
      [{ stage: :audio, elapsed_seconds: 3.125, status: 'done', concurrency: 2 }]
    )
  end

  it 'records a failed stage without swallowing its error' do
    clock = double('Clock')
    allow(clock).to receive(:call).and_return(20.0, 21.0)
    timings = described_class.new(clock: clock)

    expect { timings.measure(:audio) { raise 'audio failure' } }.to raise_error('audio failure')
    expect(timings.entries.last).to include(status: 'failed', elapsed_seconds: 1.0)
  end
end
