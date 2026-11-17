# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CopyVersionFileExport do
  let(:runner) { instance_double(VideoEncoder::CommandRunner, run: true) }
  let(:fallback) { instance_double(VideoEncoder::ExportTrimProjectFile, call: :exported) }
  let(:receipt) { instance_double(VideoEncoder::ExportReceipt, call: :receipt) }
  let(:json) { JSON.generate(format: 'video_encoder.copy_version', version: 2) }
  let(:reader) { class_double(File, read: json) }
  let(:service) do
    described_class.new(fallback: fallback, runner: runner, workspace_directory: '/exports/work',
                        reader: reader, receipt: receipt)
  end

  it 'uses the queued lossless pipeline and emits the normal receipt only after success' do
    service.call(project_path: '/projects/version.json', output_path: '/exports/version.mkv')
    script = File.expand_path('../lib/video_encoder/copy_version_pipeline.py', __dir__)
    expect(runner).to have_received(:run).with('python3', script, 'export', '/projects/version.json',
                                               '/exports/version.mkv', '/exports/work')
    expect(receipt).to have_received(:call).with(project_path: '/projects/version.json', project_json: json,
                                                 trim_project: nil, output_path: '/exports/version.mkv',
                                                 audio_roles: ['original'])
    expect(fallback).not_to have_received(:call)
  end

  it 'does not emit a success receipt if the source changed or remux failed' do
    allow(runner).to receive(:run).and_raise(RuntimeError, 'source changed')
    expect { service.call(project_path: 'version.json', output_path: 'version.mkv') }.to raise_error('source changed')
    expect(receipt).not_to have_received(:call)
  end

  it 'preserves the existing DVD and montage dispatch' do
    allow(reader).to receive(:read).and_return('{"format":"video_encoder.trim_project","version":2}')
    expect(service.call(project_path: 'tv.json', output_path: 'tv.mkv')).to eq(:exported)
    expect(runner).not_to have_received(:run)
    dvd = JSON.generate(format: 'video_encoder.dvd_project', version: 2, dvd: { audio: [{ role: 'french' }] })
    allow(reader).to receive(:read).and_return(dvd)
    service.call(project_path: 'dvd.json', output_path: 'dvd.mkv')
    expect(runner).to have_received(:run).with('python3', /dvd_pipeline.py\z/, 'export',
                                               'dvd.json', 'dvd.mkv', '/exports/work')
  end

  it 'retains source usage so queued conversions protect their input copy' do
    document = JSON.generate(format: 'video_encoder.copy_version', version: 2,
                             sources: [{ path: '/videos/source.mkv' }])
    expect(VideoEncoder::TrimProjectSourcePaths.new.call(document)).to eq([Pathname('/videos/source.mkv')])
  end
end
