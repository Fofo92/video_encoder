# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::DvdProjectFileExport do
  let(:runner) { instance_double(VideoEncoder::CommandRunner, run: true) }
  let(:fallback) { instance_double(VideoEncoder::ExportTrimProjectFile, call: :exported) }
  let(:receipt) { instance_double(VideoEncoder::ExportReceipt, call: :receipt) }
  let(:reader) { class_double(File, read: json) }
  let(:json) do
    JSON.generate(format: 'video_encoder.dvd_project', version: 2,
                  dvd: { audio: [{ role: 'french' }, { role: 'original' }] })
  end
  let(:service) do
    described_class.new(fallback: fallback, runner: runner, workspace_directory: '/exports/work',
                        reader: reader, receipt: receipt)
  end

  it 'runs the whole-title pipeline and reuses the vidb export receipt' do
    service.call(project_path: '/projects/dvd.json', output_path: '/exports/dvd.mkv')
    script = File.expand_path('../lib/video_encoder/dvd_pipeline.py', __dir__)
    expect(runner).to have_received(:run).with('python3', script, 'export', '/projects/dvd.json',
                                               '/exports/dvd.mkv', '/exports/work')
    expect(receipt).to have_received(:call).with(project_path: '/projects/dvd.json', project_json: json,
                                                 trim_project: nil, output_path: '/exports/dvd.mkv',
                                                 audio_roles: %w[french original])
    expect(fallback).not_to have_received(:call)
  end

  it 'keeps ordinary TV montage exports on their existing pipeline' do
    allow(reader).to receive(:read).and_return('{"format":"video_encoder.trim_project","version":2}')
    expect(service.call(project_path: 'tv.json', output_path: 'tv.mkv')).to eq(:exported)
    expect(runner).not_to have_received(:run)
    expect(receipt).not_to have_received(:call)
  end

  it 'never issues a completed receipt after an encoder failure' do
    allow(runner).to receive(:run).and_raise(RuntimeError, 'encoding failed')
    expect { service.call(project_path: 'dvd.json', output_path: 'dvd.mkv') }.to raise_error('encoding failed')
    expect(receipt).not_to have_received(:call)
  end
  it 'keeps source references stable when relocating a DVD project' do
    json = JSON.generate(format: 'video_encoder.dvd_project', version: 2,
                         sources: [{ path: 'local-copy.mkv' }])
    document = VideoEncoder::ProjectRelocationDocument.new('/videos/DVD.json', bytes: json)
    moved = JSON.parse(document.bytes)
    expect(moved.fetch('sources').first.fetch('path')).to eq(File.expand_path('local-copy.mkv'))
  end
end
