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
    it 'returns a temporary path identified by the output role' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)

        output_track = instance_double(
          VideoEncoder::AudioOutputTrack,
          role: :french
        )

        expect(workspace.audio_path(output_track)).to eq(
          File.join(directory, 'audio_french.mka')
        )
      end
    end
  end

  describe '#subtitle_transport_path' do
    it 'returns a transport stream path identified by segment index' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)

        expect(workspace.subtitle_transport_path(2)).to eq(
          File.join(directory, 'subtitle_segment_2.ts')
        )
      end
    end
  end

  describe '#subtitle_srt_path' do
    it 'returns an SRT path identified by segment index' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)

        expect(workspace.subtitle_srt_path(2)).to eq(
          File.join(directory, 'subtitle_segment_2.srt')
        )
      end
    end
  end
  describe '#subtitle_path' do
    it 'returns the composed subtitle path' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)

        expect(workspace.subtitle_path).to eq(
          File.join(directory, 'subtitles.srt')
        )
      end
    end
  end

  describe '#write_subtitles' do
    it 'writes the composed SRT document' do
      Dir.mktmpdir do |directory|
        workspace = described_class.new(directory: directory)

        workspace.write_subtitles("1\n00:00:01,000 --> 00:00:02,000\nTexte.\n")

        expect(
          File.read(File.join(directory, 'subtitles.srt'))
        ).to eq(
          "1\n00:00:01,000 --> 00:00:02,000\nTexte.\n"
        )
      end
    end
  end
end
