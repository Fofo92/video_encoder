# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'

RSpec.describe VideoEncoder::TrimWorkspace do
  describe '#write_mlt' do
    it 'writes the MLT project' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)

        workspace.write_mlt('<mlt/>')

        expect(
          File.read(File.join(directory, 'project.mlt'))
        ).to eq('<mlt/>')
      end
    end
  end

  describe '#video_path' do
    it 'returns the temporary video path' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)

        expect(workspace.video_path).to eq(
          File.join(directory, 'video.mkv')
        )
      end
    end
  end

  describe '#audio_path' do
    it 'returns the temporary path for an audio track' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)
        track = instance_double(VideoEncoder::Track, index: 1)

        expect(workspace.audio_path(track)).to eq(
          File.join(directory, 'audio_1.mka')
        )
      end
    end
  end

  describe '#audio_path' do
    it 'returns the temporary path for an audio track' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)

        track = instance_double(VideoEncoder::Track, index: 1)

        expect(workspace.audio_path(track)).to eq(
          File.join(directory, 'audio_1.mka')
        )
      end
    end
  end
end
