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
  let(:workspace) { instance_double(VideoEncoder::TrimWorkspace) }

  describe '#call' do
    it 'builds an audio project from the tracks selected for each source' do
      media_a = instance_double(VideoEncoder::Media)
      media_c = instance_double(VideoEncoder::Media)
      track_a = instance_double(VideoEncoder::Track)
      track_c = instance_double(VideoEncoder::Track)
      video_a = instance_double(VideoEncoder::VideoTrack)
      video_c = instance_double(VideoEncoder::VideoTrack)

      segment_a = instance_double(VideoEncoder::Segment, source: media_a)
      segment_c = instance_double(VideoEncoder::Segment, source: media_c)

      trim_project = instance_double(
        VideoEncoder::TrimProject,
        segments: [segment_a, segment_c]
      )

      output_track = instance_double(
        VideoEncoder::AudioOutputTrack,
        role: :french
      )

      allow(output_track)
        .to receive(:complete_for?)
        .with([media_a, media_c])
        .and_return(true)

      allow(output_track).to receive(:track_for)
        .with(media_a)
        .and_return(track_a)

      allow(output_track).to receive(:track_for)
        .with(media_c)
        .and_return(track_c)

      allow(builder).to receive(:build).and_return('<mlt/>')
      allow(workspace).to receive(:write_mlt)
      allow(workspace).to receive(:mlt_path).and_return('tmp/project.mlt')
      allow(workspace).to receive(:video_path).and_return('tmp/video.mkv')
      allow(workspace)
        .to receive(:audio_path)
        .with(output_track)
        .and_return('tmp/audio_french.mka')

      allow(renderer).to receive(:render_video)
      allow(renderer).to receive(:render_audio)
      allow(remuxer).to receive(:remux)

      exporter.call(
        trim_project: trim_project,
        video_tracks_by_source: {
          media_a => video_a,
          media_c => video_c
        },
        audio_output_tracks: [output_track],
        output_path: 'movie.mkv'
      )

      expect(builder).to have_received(:build).with(
        trim_project,
        audio_index: -1,
        video_tracks_by_source: {
          media_a => video_a,
          media_c => video_c
        }
      )

      expect(builder).to have_received(:build).with(
        trim_project,
        video_index: -1,
        audio_tracks_by_source: {
          media_a => track_a,
          media_c => track_c
        }
      )
    end
    it 'omits an audio output that does not cover every source' do
      video_a = instance_double(VideoEncoder::VideoTrack)
      video_c = instance_double(VideoEncoder::VideoTrack)

      media_a = instance_double(VideoEncoder::Media)
      media_c = instance_double(VideoEncoder::Media)

      segment_a = instance_double(VideoEncoder::Segment, source: media_a)
      segment_c = instance_double(VideoEncoder::Segment, source: media_c)

      trim_project = instance_double(
        VideoEncoder::TrimProject,
        segments: [segment_a, segment_c]
      )

      output_track = instance_double(
        VideoEncoder::AudioOutputTrack,
        role: :original
      )

      allow(output_track)
        .to receive(:complete_for?)
        .with([media_a, media_c])
        .and_return(false)

      allow(builder).to receive(:build).and_return('<video-mlt/>')
      allow(workspace).to receive(:write_mlt)
      allow(workspace).to receive(:mlt_path).and_return('tmp/project.mlt')
      allow(workspace).to receive(:video_path).and_return('tmp/video.mkv')
      allow(renderer).to receive(:render_video)
      allow(renderer).to receive(:render_audio)
      allow(remuxer).to receive(:remux)

      exporter.call(
        trim_project: trim_project,
        video_tracks_by_source: {
          media_a => video_a,
          media_c => video_c
        },
        audio_output_tracks: [output_track],
        output_path: 'movie.mkv'
      )

      expect(builder).to have_received(:build).once
      expect(renderer).not_to have_received(:render_audio)

      expect(remuxer).to have_received(:remux).with(
        video_path: 'tmp/video.mkv',
        audio_inputs: [],
        output_path: 'movie.mkv'
      )
    end
  end
end
