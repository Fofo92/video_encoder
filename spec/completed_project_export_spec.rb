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

  it 'never publishes a failed export' do
    allow(exporter).to receive(:call).and_raise('encoding failed')
    expect(receipt).not_to receive(:call)
    expect { service.call(project_path: 'project.json', output_path: 'final.mkv') }.to raise_error('encoding failed')
  end
end
