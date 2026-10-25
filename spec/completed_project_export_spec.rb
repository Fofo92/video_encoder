# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ExportTrimProjectFile do
  let(:exporter) { double(call: :exported) }
  let(:receipt) { double(call: nil) }
  let(:project) { double('project') }
  let(:reader) { double(read: '{}') }
  let(:loader) { double(load: project) }
  let(:service) { described_class.new(reader: reader, loader: loader, exporter: exporter, receipt: receipt) }

  it 'publishes only after the export succeeds and preserves its result' do
    expect(exporter).to receive(:call).ordered.and_return(:exported)
    expect(receipt).to receive(:call).with(project_path: 'project.json', project_json: '{}',
                                           trim_project: project, output_path: 'final.mkv').ordered
    expect(service.call(project_path: 'project.json', output_path: 'final.mkv')).to eq(:exported)
  end

  it 'includes measured stage durations in the existing receipt after success' do
    clock = double('Clock')
    allow(clock).to receive(:call).and_return(20.0, 23.0)
    timings = VideoEncoder::ExportTimings.new(clock: clock)
    allow(exporter).to receive(:call) { timings.measure(:audio, concurrency: 2) { :exported } }
    service = described_class.new(
      reader: reader, loader: loader, exporter: exporter, receipt: receipt, timings: timings
    )

    expect(service.call(project_path: 'project.json', output_path: 'final.mkv')).to eq(:exported)
    expect(receipt).to have_received(:call).with(
      project_path: 'project.json', project_json: '{}', trim_project: project, output_path: 'final.mkv',
      timings: [{ stage: :audio, elapsed_seconds: 3.0, status: 'done', concurrency: 2 }]
    )
  end

  it 'never publishes a failed export' do
    allow(exporter).to receive(:call).and_raise('encoding failed')
    expect(receipt).not_to receive(:call)
    expect { service.call(project_path: 'project.json', output_path: 'final.mkv') }.to raise_error('encoding failed')
  end
end
