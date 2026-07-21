# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Workspace do
  let(:directories) do
    instance_double(
      VideoEncoder::Directories,
      encoding: '/commun/Encoding',
      encoded: '/commun/Encoded',
      archive: '/commun/Archive'
    )
  end

  subject(:workspace) do
    described_class.new(directories: directories)
  end

  before do
    allow(FileUtils).to receive(:mv)
    allow(FileUtils).to receive(:rm_f)
    allow(File).to receive(:exist?).and_return(true)
  end

  describe '#move_to_encoding' do
    it 'moves the source file to Encoding' do
      workspace.move_to_encoding('video.m2t')

      expect(FileUtils)
        .to have_received(:mv)
        .with('video.m2t', '/commun/Encoding/video.m2t')
    end
  end

  describe '#move_to_encoded' do
    it 'moves the encoded file to Encoded' do
      workspace.move_to_encoded('video.mkv')

      expect(FileUtils)
        .to have_received(:mv)
        .with('video.mkv', '/commun/Encoded/video.mkv')
    end

    it 'removes the temporary encoded suffix' do
      result = workspace.move_to_encoded('video.encoded.mkv')

      expect(FileUtils)
        .to have_received(:mv)
        .with(
          'video.encoded.mkv',
          '/commun/Encoded/video.mkv'
        )

      expect(result).to eq('/commun/Encoded/video.mkv')
    end
  end

  describe '#move_to_archive' do
    it 'moves the source file to Archive' do
      workspace.move_to_archive('video.m2t')

      expect(FileUtils)
        .to have_received(:mv)
        .with('video.m2t', '/commun/Archive/video.m2t')
    end
  end

  describe '#remove_partial_output' do
    it 'removes the partial output file' do
      workspace.remove_partial_output('video.mkv')

      expect(FileUtils)
        .to have_received(:rm_f)
        .with('video.mkv')
    end
  end

  describe '#finalize' do
    it 'moves the encoded file then archives the source' do
      workspace.finalize(
        source: 'video.m2t',
        output: 'video.mkv'
      )

      expect(FileUtils)
        .to have_received(:mv)
        .with('video.mkv', '/commun/Encoded/video.mkv')
        .ordered

      expect(FileUtils)
        .to have_received(:mv)
        .with('video.m2t', '/commun/Archive/video.m2t')
        .ordered
    end
  end
end
