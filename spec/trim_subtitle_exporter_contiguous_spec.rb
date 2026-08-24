# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimSubtitleExporter do
  it 'processes contiguous eligible segments in one subtitle project' do
    processor = instance_double(VideoEncoder::SubtitleProjectProcessor)
    composer = instance_double(VideoEncoder::SrtComposer)
    workspace = instance_double(VideoEncoder::TrimWorkspace)

    exporter = described_class.new(
      processor: processor,
      composer: composer,
      workspace: workspace
    )

    media_a = instance_double(VideoEncoder::Media)
    media_c = instance_double(VideoEncoder::Media)

    segment_a = instance_double(
      VideoEncoder::Segment,
      source: media_a,
      start_frame: 30_000,
      end_frame: 31_499
    )

    segment_c = instance_double(
      VideoEncoder::Segment,
      source: media_c,
      start_frame: 30_000,
      end_frame: 31_499
    )

    video_a = instance_double(
      VideoEncoder::VideoTrack,
      frame_rate: Rational(25, 1)
    )

    video_c = instance_double(
      VideoEncoder::VideoTrack,
      frame_rate: Rational(25, 1)
    )

    segment_a3 = instance_double(
      VideoEncoder::Segment,
      source: media_a,
      start_frame: 33_000,
      end_frame: 34_499
    )

    subtitle_a = instance_double(VideoEncoder::Track)
    subtitle_c = instance_double(VideoEncoder::Track)

    allow(workspace).to receive(:subtitle_transport_path)
      .with(0).and_return('/tmp/subtitle_segment_0.ts')
    allow(workspace).to receive(:subtitle_transport_path)
      .with(1).and_return('/tmp/subtitle_segment_1.ts')
    allow(workspace).to receive(:subtitle_transport_path)
      .with(2).and_return('/tmp/subtitle_segment_2.ts')
    allow(workspace).to receive(:subtitle_manifest_path)
      .with(0).and_return('/tmp/subtitle_project_0.ffconcat')
    allow(workspace).to receive(:subtitle_project_transport_path)
      .with(0).and_return('/tmp/subtitle_project_0.ts')
    allow(workspace).to receive(:subtitle_project_srt_path)
      .with(0).and_return('/tmp/subtitle_project_0.srt')
    allow(workspace).to receive(:subtitle_path)
      .and_return('/tmp/subtitles.srt')
    allow(workspace).to receive(:write_subtitles)

    allow(processor).to receive(:call)
      .and_return("normalized project\n")
    allow(composer).to receive(:call)
      .with(["normalized project\n"])
      .and_return("composed subtitles\n")

    project = instance_double(
      VideoEncoder::TrimProject,
      segments: [segment_a, segment_c, segment_a3]
    )

    exporter.call(
      trim_project: project,
      video_tracks_by_source: {
        media_a => video_a,
        media_c => video_c
      },
      subtitle_tracks_by_source: {
        media_a => subtitle_a,
        media_c => subtitle_c
      }
    )

    expect(processor).to have_received(:call).once.with(
      segments: [
        {
          segment: segment_a,
          video_track: video_a,
          subtitle_track: subtitle_a,
          transport_path: '/tmp/subtitle_segment_0.ts'
        },
        {
          segment: segment_c,
          video_track: video_c,
          subtitle_track: subtitle_c,
          transport_path: '/tmp/subtitle_segment_1.ts'
        },
        {
          segment: segment_a3,
          video_track: video_a,
          subtitle_track: subtitle_a,
          transport_path: '/tmp/subtitle_segment_2.ts'
        }
      ],
      timeline_start: 0,
      manifest_path: '/tmp/subtitle_project_0.ffconcat',
      transport_path: '/tmp/subtitle_project_0.ts',
      srt_path: '/tmp/subtitle_project_0.srt'
    )
  end
end
