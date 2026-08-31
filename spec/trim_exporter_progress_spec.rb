# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExporter, 'progress reporting' do
  let(:media) { instance_double(VideoEncoder::Media) }
  let(:segment) { instance_double(VideoEncoder::Segment, source: media) }

  let(:project) do
    instance_double(
      VideoEncoder::TrimProject,
      segments: [segment]
    )
  end

  let(:video_track) do
    instance_double(VideoEncoder::VideoTrack)
  end

  let(:source_audio_track) do
    instance_double(VideoEncoder::Track)
  end

  let(:audio_output_track) do
    instance_double(
      VideoEncoder::AudioOutputTrack,
      role: :french
    )
  end

  let(:builder) do
    instance_double(VideoEncoder::MltProjectBuilder)
  end

  let(:renderer) do
    instance_double(VideoEncoder::MltRenderer)
  end

  let(:remuxer) do
    instance_double(VideoEncoder::FfmpegRemuxer)
  end

  let(:workspace) do
    instance_double(VideoEncoder::TrimWorkspace)
  end

  let(:subtitle_exporter) do
    instance_double(VideoEncoder::TrimSubtitleExporter)
  end

  it 'reports every export stage in order' do
    events = []

    allow(audio_output_track)
      .to receive(:complete_for?)
      .with([media])
      .and_return(true)

    allow(audio_output_track)
      .to receive(:track_for)
      .with(media)
      .and_return(source_audio_track)

    allow(builder).to receive(:build)
      .and_return('<mlt/>')

    allow(workspace).to receive_messages(
      write_mlt: nil,
      mlt_path: 'tmp/project.mlt',
      video_path: 'tmp/video.mkv'
    )

    allow(workspace)
      .to receive(:audio_path)
      .with(audio_output_track)
      .and_return('tmp/audio.mka')

    allow(renderer).to receive_messages(
      render_video: nil,
      render_audio: nil
    )

    allow(subtitle_exporter)
      .to receive(:call)
      .and_return(nil)

    allow(remuxer).to receive(:remux)

    exporter = described_class.new(
      builder: builder,
      renderer: renderer,
      remuxer: remuxer,
      workspace: workspace,
      subtitle_exporter: subtitle_exporter,
      progress_reporter: ->(**event) { events << event }
    )

    exporter.call(
      trim_project: project,
      video_tracks_by_source: {
        media => video_track
      },
      audio_output_tracks: [
        audio_output_track
      ],
      output_path: 'movie.mkv'
    )

    expect(events).to eq(
      [
        {
          stage: :subtitles,
          step: 1,
          total: 4
        },
        {
          stage: :video,
          step: 2,
          total: 4
        },
        {
          stage: :audio,
          step: 3,
          total: 4,
          track: 1,
          tracks: 1,
          role: :french
        },
        {
          stage: :remux,
          step: 4,
          total: 4
        }
      ]
    )
  end
end
