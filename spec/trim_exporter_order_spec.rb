# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExporter do
  it 'renders video before extracting subtitles' do
    builder = instance_double(
      VideoEncoder::MltProjectBuilder
    )

    renderer = instance_double(
      VideoEncoder::MltRenderer
    )

    remuxer = instance_double(
      VideoEncoder::FfmpegRemuxer
    )

    workspace = instance_double(
      VideoEncoder::TrimWorkspace
    )

    subtitle_exporter = instance_double(
      VideoEncoder::TrimSubtitleExporter
    )

    media = instance_double(
      VideoEncoder::Media
    )

    segment = instance_double(
      VideoEncoder::Segment,
      source: media
    )

    trim_project = instance_double(
      VideoEncoder::TrimProject,
      segments: [segment]
    )

    video_track = instance_double(
      VideoEncoder::VideoTrack
    )

    video_tracks_by_source = {
      media => video_track
    }

    subtitle_track = instance_double(
      VideoEncoder::Track
    )

    subtitle_tracks_by_source = {
      media => subtitle_track
    }

    allow(builder)
      .to receive(:build)
      .and_return('<video-mlt/>')

    allow(workspace).to receive(:write_mlt)

    allow(workspace)
      .to receive(:mlt_path)
      .and_return('tmp/project.mlt')

    allow(workspace)
      .to receive(:video_path)
      .and_return('tmp/video.mkv')

    allow(remuxer).to receive(:remux)

    expect(renderer)
      .to receive(:render_video)
      .with(
        project_path: 'tmp/project.mlt',
        output_path: 'tmp/video.mkv'
      )
      .ordered

    expect(subtitle_exporter)
      .to receive(:call)
      .with(
        trim_project: trim_project,
        video_tracks_by_source:
          video_tracks_by_source,
        subtitle_tracks_by_source:
          subtitle_tracks_by_source
      )
      .ordered
      .and_return(nil)

    described_class.new(
      builder: builder,
      renderer: renderer,
      remuxer: remuxer,
      workspace: workspace,
      subtitle_exporter: subtitle_exporter
    ).call(
      trim_project: trim_project,
      video_tracks_by_source:
        video_tracks_by_source,
      audio_output_tracks: [],
      subtitle_tracks_by_source:
        subtitle_tracks_by_source,
      output_path: 'movie.mkv'
    )
  end
end
