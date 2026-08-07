# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExporter do
  subject(:exporter) do
    described_class.new(
      builder: builder,
      renderer: renderer,
      remuxer: remuxer,
      workspace: workspace
    )
  end

  let(:builder) { instance_double(VideoEncoder::MltProjectBuilder) }
  let(:renderer) { instance_double(VideoEncoder::MltRenderer) }
  let(:remuxer) { instance_double(VideoEncoder::FfmpegRemuxer) }
  let(:workspace) { instance_double('TrimWorkspace') }

  let(:trim_project) { instance_double(VideoEncoder::TrimProject) }
  let(:audio_track) { instance_double(VideoEncoder::Track) }

  describe '#call' do
    it 'exports a trimmed movie' do
      allow(workspace).to receive(:mlt_path).and_return('tmp/project.mlt')
      allow(workspace).to receive(:video_path).and_return('tmp/video.mkv')
      allow(workspace)
        .to receive(:audio_path)
        .with(audio_track)
        .and_return('tmp/audio_1.mka')

      allow(builder).to receive(:build).with(trim_project)
      allow(workspace).to receive(:write_mlt)
      allow(renderer).to receive(:render_video)
      allow(renderer).to receive(:render_audio)
      allow(remuxer).to receive(:remux)

      exporter.call(
        trim_project: trim_project,
        tracks: [audio_track],
        output_path: 'movie.mkv'
      )

      expect(builder).to have_received(:build).with(trim_project)

      expect(renderer).to have_received(:render_video).with(
        project_path: 'tmp/project.mlt',
        output_path: 'tmp/video.mkv'
      )

      expect(renderer).to have_received(:render_audio).with(
        project_path: 'tmp/project.mlt',
        output_path: 'tmp/audio_1.mka'
      )

      expect(remuxer).to have_received(:remux).with(
        video_path: 'tmp/video.mkv',
        audio_inputs: [
          {
            path: 'tmp/audio_1.mka',
            track: audio_track
          }
        ],
        output_path: 'movie.mkv'
      )
    end
  end

  it 'writes the generated MLT project to the workspace' do
    xml = '<mlt/>'

    allow(builder).to receive(:build)
      .with(trim_project)
      .and_return(xml)

    allow(workspace).to receive(:mlt_path).and_return('tmp/project.mlt')
    allow(workspace).to receive(:video_path).and_return('tmp/video.mkv')
    allow(workspace)
      .to receive(:audio_path)
      .with(audio_track)
      .and_return('tmp/audio_1.mka')

    allow(workspace).to receive(:write_mlt)
    allow(renderer).to receive(:render_video)
    allow(renderer).to receive(:render_audio)
    allow(remuxer).to receive(:remux)

    exporter.call(
      trim_project: trim_project,
      tracks: [audio_track],
      output_path: 'movie.mkv'
    )

    expect(workspace).to have_received(:write_mlt).with(xml)
  end

  it 'renders each selected audio track separately' do
    french_track = instance_double(VideoEncoder::Track)
    english_track = instance_double(VideoEncoder::Track)

    allow(builder).to receive(:build).with(trim_project).and_return('<mlt/>')

    allow(workspace).to receive(:write_mlt)
    allow(workspace).to receive(:mlt_path).and_return('tmp/project.mlt')
    allow(workspace).to receive(:video_path).and_return('tmp/video.mkv')

    allow(workspace)
      .to receive(:audio_path)
      .with(french_track)
      .and_return('tmp/audio_fra.mka')

    allow(workspace)
      .to receive(:audio_path)
      .with(english_track)
      .and_return('tmp/audio_eng.mka')

    allow(renderer).to receive(:render_video)
    allow(renderer).to receive(:render_audio)
    allow(remuxer).to receive(:remux)

    exporter.call(
      trim_project: trim_project,
      tracks: [french_track, english_track],
      output_path: 'movie.mkv'
    )

    expect(renderer).to have_received(:render_audio).with(
      project_path: 'tmp/project.mlt',
      output_path: 'tmp/audio_fra.mka'
    )

    expect(renderer).to have_received(:render_audio).with(
      project_path: 'tmp/project.mlt',
      output_path: 'tmp/audio_eng.mka'
    )

    expect(remuxer).to have_received(:remux).with(
      video_path: 'tmp/video.mkv',
      audio_inputs: [
        {
          path: 'tmp/audio_fra.mka',
          track: french_track
        },
        {
          path: 'tmp/audio_eng.mka',
          track: english_track
        }
      ],
      output_path: 'movie.mkv'
    )
  end
end
