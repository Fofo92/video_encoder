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

  let(:media) { instance_double(VideoEncoder::Media) }
  let(:segment) { instance_double(VideoEncoder::Segment, source: media) }

  let(:trim_project) do
    instance_double(
      VideoEncoder::TrimProject,
      segments: [segment]
    )
  end

  let(:source_track) { instance_double(VideoEncoder::Track) }

  let(:audio_output_track) do
    instance_double(
      VideoEncoder::AudioOutputTrack,
      role: :french
    )
  end

  before do
    allow(audio_output_track)
      .to receive(:complete_for?)
      .with([media])
      .and_return(true)

    allow(audio_output_track)
      .to receive(:track_for)
      .with(media)
      .and_return(source_track)
  end

  describe '#call' do
    it 'exports a trimmed movie' do
      allow(workspace).to receive(:mlt_path).and_return('tmp/project.mlt')
      allow(workspace).to receive(:video_path).and_return('tmp/video.mkv')
      allow(workspace)
        .to receive(:audio_path)
        .with(audio_output_track)
        .and_return('tmp/audio_french.mka')

      allow(builder).to receive(:build).and_return('<mlt/>')
      allow(workspace).to receive(:write_mlt)
      allow(renderer).to receive(:render_video)
      allow(renderer).to receive(:render_audio)
      allow(remuxer).to receive(:remux)

      exporter.call(
        trim_project: trim_project,
        audio_output_tracks: [audio_output_track],
        output_path: 'movie.mkv'
      )

      expect(builder).to have_received(:build).with(
        trim_project,
        audio_index: -1
      )

      expect(builder).to have_received(:build).with(
        trim_project,
        video_index: -1,
        audio_tracks_by_source: {
          media => source_track
        }
      )

      expect(renderer).to have_received(:render_video).with(
        project_path: 'tmp/project.mlt',
        output_path: 'tmp/video.mkv'
      )

      expect(renderer).to have_received(:render_audio).with(
        project_path: 'tmp/project.mlt',
        output_path: 'tmp/audio_french.mka'
      )

      expect(remuxer).to have_received(:remux).with(
        video_path: 'tmp/video.mkv',
        audio_inputs: [
          {
            path: 'tmp/audio_french.mka',
            output_track: audio_output_track
          }
        ],
        output_path: 'movie.mkv'
      )
    end
  end

  it 'writes each generated MLT project to the workspace' do
    allow(builder)
      .to receive(:build)
      .and_return('<video-mlt/>', '<audio-mlt/>')

    allow(workspace).to receive(:write_mlt)
    allow(workspace).to receive(:mlt_path).and_return('tmp/project.mlt')
    allow(workspace).to receive(:video_path).and_return('tmp/video.mkv')

    allow(workspace)
      .to receive(:audio_path)
      .with(audio_output_track)
      .and_return('tmp/audio_french.mka')

    allow(renderer).to receive(:render_video)
    allow(renderer).to receive(:render_audio)
    allow(remuxer).to receive(:remux)

    exporter.call(
      trim_project: trim_project,
      audio_output_tracks: [audio_output_track],
      output_path: 'movie.mkv'
    )

    expect(workspace).to have_received(:write_mlt)
      .with('<video-mlt/>')
      .ordered

    expect(workspace).to have_received(:write_mlt)
      .with('<audio-mlt/>')
      .ordered
  end

  it 'renders each selected audio output separately' do
    original_source_track = instance_double(VideoEncoder::Track)

    original_output_track = instance_double(
      VideoEncoder::AudioOutputTrack,
      role: :original
    )

    allow(original_output_track)
      .to receive(:complete_for?)
      .with([media])
      .and_return(true)

    allow(original_output_track)
      .to receive(:track_for)
      .with(media)
      .and_return(original_source_track)

    allow(builder)
      .to receive(:build)
      .and_return('<video-mlt/>', '<french-mlt/>', '<original-mlt/>')

    allow(workspace).to receive(:write_mlt)
    allow(workspace).to receive(:mlt_path).and_return('tmp/project.mlt')
    allow(workspace).to receive(:video_path).and_return('tmp/video.mkv')

    allow(workspace)
      .to receive(:audio_path)
      .with(audio_output_track)
      .and_return('tmp/audio_french.mka')

    allow(workspace)
      .to receive(:audio_path)
      .with(original_output_track)
      .and_return('tmp/audio_original.mka')

    allow(renderer).to receive(:render_video)
    allow(renderer).to receive(:render_audio)
    allow(remuxer).to receive(:remux)

    exporter.call(
      trim_project: trim_project,
      audio_output_tracks: [
        audio_output_track,
        original_output_track
      ],
      output_path: 'movie.mkv'
    )

    expect(renderer).to have_received(:render_audio).with(
      project_path: 'tmp/project.mlt',
      output_path: 'tmp/audio_french.mka'
    )

    expect(renderer).to have_received(:render_audio).with(
      project_path: 'tmp/project.mlt',
      output_path: 'tmp/audio_original.mka'
    )

    expect(remuxer).to have_received(:remux).with(
      video_path: 'tmp/video.mkv',
      audio_inputs: [
        {
          path: 'tmp/audio_french.mka',
          output_track: audio_output_track
        },
        {
          path: 'tmp/audio_original.mka',
          output_track: original_output_track
        }
      ],
      output_path: 'movie.mkv'
    )
  end
end
