# frozen_string_literal: true

require 'spec_helper'
require 'json'
require 'tmpdir'

RSpec.describe VideoEncoder::ExportReceipt do
  it 'carries the stable project identity and only the validated binding fields' do
    json = JSON.generate(
      project_id: '4d013c0a-7b54-4a67-aef2-7e1af7f6d410',
      vidb: {
        status: 'identified', record_id: 123, binding_token: 'signed',
        record_title: 'Film', private_note: 'ignored'
      }
    )
    result = described_class.new.send(:project_binding, json)
    expect(result['project_id']).to eq('4d013c0a-7b54-4a67-aef2-7e1af7f6d410')
    expect(result['vidb']).to eq('record_id' => 123, 'binding_token' => 'signed')
  end

  it 'keeps historical projects without a binding compatible' do
    expect(described_class.new.send(:project_binding, '{}')).to eq({})
  end

  it 'preserves processing timings alongside the project binding in the final receipt' do
    Dir.mktmpdir do |directory|
      path = File.join(directory, 'film.mkv')
      File.write(path, 'video')
      writer = described_class.new
      allow(writer).to receive(:probe).and_return({})
      allow(writer).to receive(:roles).and_return(['french'])
      json = JSON.generate(project_id: '4d013c0a-7b54-4a67-aef2-7e1af7f6d410',
                           vidb: { record_id: 123, binding_token: 'signed' })
      receipt_path = writer.call(project_path: '/videos/film.json', project_json: json,
                                 trim_project: nil, output_path: path, timings: { audio: 12.5 })
      receipt = JSON.parse(File.read(receipt_path))
      expect(receipt['timings']).to eq('audio' => 12.5)
      expect(receipt['vidb']).to eq('record_id' => 123, 'binding_token' => 'signed')
    end
  end
end
