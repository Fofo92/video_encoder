# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::MltRenderer do
  subject(:renderer) { described_class.new(runner: runner) }

  let(:runner) { instance_double('CommandRunner') }

  describe '#render_video' do
    it 'renders a video-only file with melt' do
      allow(runner).to receive(:run)

      renderer.render_video(
        project_path: 'tmp/project.mlt',
        output_path: 'tmp/video.mkv'
      )

      expect(runner).to have_received(:run).with(
        'melt-7',
        '-progress2',
        'tmp/project.mlt',
        '-consumer',
        'avformat:tmp/video.mkv',
        'vcodec=libx265',
        'crf=24',
        'preset=medium',
        'an=1'
      )
    end
  end

  describe '#render_audio' do
    it 'renders an audio-only file with melt' do
      allow(runner).to receive(:run)

      renderer.render_audio(
        project_path: 'tmp/project.mlt',
        output_path: 'tmp/audio.mka'
      )

      expect(runner).to have_received(:run).with(
        'melt-7',
        '-progress2',
        'tmp/project.mlt',
        '-consumer',
        'avformat:tmp/audio.mka',
        'acodec=aac',
        'ab=160k',
        'vn=1'
      )
    end
  end
end
