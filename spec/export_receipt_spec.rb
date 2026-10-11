# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'
require 'json'

RSpec.describe VideoEncoder::ExportReceipt do
  it 'writes the actual final path and selected roles after inspection' do
    Dir.mktmpdir do |directory|
      path = File.join(directory, 'S05 E01 - Panique.mkv')
      File.write(path, 'video')
      project = double(segments: [])
      writer = described_class.new
      allow(writer).to receive(:probe).and_return('format' => { 'duration' => '2400' }, 'streams' => [])
      allow(writer).to receive(:roles).with(project).and_return(%w[french original])
      receipt_path = writer.call(project_path: '/projects/episode.json', project_json: '{}',
                                 trim_project: project, output_path: path)
      receipt = JSON.parse(File.read(receipt_path))
      expect(receipt['output_path']).to eq(path)
      expect(receipt['roles']).to eq(%w[french original])
      expect(receipt['byte_size']).to eq(5)
      expect(receipt['project_sha256']).to eq(Digest::SHA256.hexdigest('{}'))
    end
  end

  it 'preserves export success when receipt inspection fails' do
    writer = described_class.new
    allow(writer).to receive(:warn)
    expect(writer.call(project_path: 'project', project_json: '{}', trim_project: nil,
                       output_path: '/missing/export.mkv')).to be_nil
    expect(writer).to have_received(:warn).with(/vidb receipt unavailable/)
  end

  it 'writes no receipt if the output changes while ffprobe runs' do
    Dir.mktmpdir do |directory|
      path = File.join(directory, 'output.mkv')
      File.write(path, 'video')
      writer = described_class.new
      allow(writer).to receive(:warn)
      allow(writer).to receive(:probe) do
        File.write(path, 'changed video')
        {}
      end
      expect(writer.call(project_path: 'project', project_json: '{}', trim_project: nil, output_path: path)).to be_nil
      expect(File.exist?("#{path}.video_encoder-export.json")).to be(false)
    end
  end
end
