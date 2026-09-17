# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::MltRenderer do
  subject(:renderer) { described_class.new(runner: runner) }

  let(:runner) { instance_double('CommandRunner') }

  describe '#render_video' do
    it 'renders a video-only file with melt' do
      allow(runner).to receive(:run)
      allow(File).to receive(:file?)
        .with('tmp/video.mkv')
        .and_return(true)
      allow(File).to receive(:empty?)
        .with('tmp/video.mkv')
        .and_return(false)

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

    it 'fails when melt does not create the video output' do
      allow(runner).to receive(:run)
      allow(File).to receive(:file?)
        .with('tmp/video.mkv')
        .and_return(false)

      expect do
        renderer.render_video(
          project_path: 'tmp/project.mlt',
          output_path: 'tmp/video.mkv'
        )
      end.to raise_error(
        StandardError,
        'melt did not create output: tmp/video.mkv'
      )
    end

    it 'fails when melt creates an empty video output' do
      allow(runner).to receive(:run)
      allow(File).to receive(:file?)
        .with('tmp/video.mkv')
        .and_return(true)
      allow(File).to receive(:empty?)
        .with('tmp/video.mkv')
        .and_return(true)

      expect do
        renderer.render_video(
          project_path: 'tmp/project.mlt',
          output_path: 'tmp/video.mkv'
        )
      end.to raise_error(
        VideoEncoder::MltRenderer::RenderFailed,
        'melt did not create output: tmp/video.mkv'
      )
    end
  end

  describe '#render_audio' do
    it 'renders an audio-only file with melt' do
      allow(runner).to receive(:run)
      allow(File).to receive(:file?)
        .with('tmp/audio.mka')
        .and_return(true)
      allow(File).to receive(:empty?)
        .with('tmp/audio.mka')
        .and_return(false)

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
