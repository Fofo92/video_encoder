# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExporter do
  describe '#call with subtitles' do
    it 'adds the composed subtitle track to the final remux' do
      builder = instance_double(VideoEncoder::MltProjectBuilder)
      renderer = instance_double(VideoEncoder::MltRenderer)
      remuxer = instance_double(VideoEncoder::FfmpegRemuxer)
      workspace = instance_double(VideoEncoder::TrimWorkspace)

      subtitle_exporter = instance_double(
        VideoEncoder::TrimSubtitleExporter
      )

      media = instance_double(VideoEncoder::Media)
      segment = instance_double(
        VideoEncoder::Segment,
        source: media
      )

      project = instance_double(
        VideoEncoder::TrimProject,
        segments: [segment]
      )

      video_track = instance_double(VideoEncoder::VideoTrack)
      subtitle_track = instance_double(VideoEncoder::Track)

      video_tracks_by_source = { media => video_track }
      subtitle_tracks_by_source = { media => subtitle_track }

      allow(builder).to receive(:build).and_return('<mlt/>')
      allow(workspace).to receive(:write_mlt)
      allow(workspace).to receive(:mlt_path)
        .and_return('tmp/project.mlt')
      allow(workspace).to receive(:video_path)
        .and_return('tmp/video.mkv')
      allow(renderer).to receive(:render_video)
      allow(remuxer).to receive(:remux)

      allow(subtitle_exporter).to receive(:call)
        .and_return('tmp/subtitles.srt')

      exporter = described_class.new(
        builder: builder,
        renderer: renderer,
        remuxer: remuxer,
        workspace: workspace,
        subtitle_exporter: subtitle_exporter
      )

      exporter.call(
        trim_project: project,
        video_tracks_by_source: video_tracks_by_source,
        audio_output_tracks: [],
        subtitle_tracks_by_source: subtitle_tracks_by_source,
        output_path: 'movie.mkv'
      )

      expect(subtitle_exporter).to have_received(:call).with(
        trim_project: project,
        video_tracks_by_source: video_tracks_by_source,
        subtitle_tracks_by_source: subtitle_tracks_by_source
      )

      expect(remuxer).to have_received(:remux).with(
        video_path: 'tmp/video.mkv',
        audio_inputs: [],
        subtitle_path: 'tmp/subtitles.srt',
        output_path: 'movie.mkv'
      )
    end
  end
end
