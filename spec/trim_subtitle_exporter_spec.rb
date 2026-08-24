# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimSubtitleExporter do
  subject(:exporter) do
    described_class.new(
      processor: processor,
      composer: composer,
      workspace: workspace
    )
  end

  let(:processor) do
    instance_double(VideoEncoder::SubtitleProjectProcessor)
  end

  let(:composer) { instance_double(VideoEncoder::SrtComposer) }
  let(:workspace) { instance_double(VideoEncoder::TrimWorkspace) }

  describe '#call' do
    it 'processes eligible segments at their project timeline position' do
      media_without_subtitles = instance_double(VideoEncoder::Media)
      media_with_subtitles = instance_double(VideoEncoder::Media)

      first_segment = instance_double(
        VideoEncoder::Segment,
        source: media_without_subtitles,
        start_frame: 0,
        end_frame: 1_499
      )

      second_segment = instance_double(
        VideoEncoder::Segment,
        source: media_with_subtitles,
        start_frame: 30_000,
        end_frame: 31_499
      )

      project = instance_double(
        VideoEncoder::TrimProject,
        segments: [first_segment, second_segment]
      )

      first_video = instance_double(
        VideoEncoder::VideoTrack,
        frame_rate: Rational(25, 1)
      )

      second_video = instance_double(
        VideoEncoder::VideoTrack,
        frame_rate: Rational(25, 1)
      )

      subtitle = instance_double(VideoEncoder::Track)

      allow(workspace).to receive(:subtitle_transport_path)
        .with(1)
        .and_return('/tmp/subtitle_segment_1.ts')

      allow(workspace).to receive(:subtitle_manifest_path)
        .with(0)
        .and_return('/tmp/subtitle_project_0.ffconcat')

      allow(workspace).to receive(:subtitle_project_transport_path)
        .with(0)
        .and_return('/tmp/subtitle_project_0.ts')

      allow(workspace).to receive(:subtitle_project_srt_path)
        .with(0)
        .and_return('/tmp/subtitle_project_0.srt')

      allow(processor).to receive(:call)
        .and_return("normalized segment\n")

      allow(composer).to receive(:call)
        .with(["normalized segment\n"])
        .and_return("composed subtitles\n")

      allow(workspace).to receive(:write_subtitles)
      allow(workspace).to receive(:subtitle_path)
        .and_return('/tmp/subtitles.srt')

      result = exporter.call(
        trim_project: project,
        video_tracks_by_source: {
          media_without_subtitles => first_video,
          media_with_subtitles => second_video
        },
        subtitle_tracks_by_source: {
          media_with_subtitles => subtitle
        }
      )

      expect(processor).to have_received(:call).with(
        segments: [
          {
            segment: second_segment,
            video_track: second_video,
            subtitle_track: subtitle,
            transport_path: '/tmp/subtitle_segment_1.ts'
          }
        ],
        timeline_start: 60,
        manifest_path: '/tmp/subtitle_project_0.ffconcat',
        transport_path: '/tmp/subtitle_project_0.ts',
        srt_path: '/tmp/subtitle_project_0.srt'
      )

      expect(workspace).to have_received(:write_subtitles)
        .with("composed subtitles\n")

      expect(result).to eq('/tmp/subtitles.srt')
    end

    it 'does not write a subtitle file when no segment is eligible' do
      project = instance_double(
        VideoEncoder::TrimProject,
        segments: []
      )

      allow(composer).to receive(:call)
        .with([])
        .and_return('')

      allow(workspace).to receive(:write_subtitles)

      result = exporter.call(
        trim_project: project,
        video_tracks_by_source: {},
        subtitle_tracks_by_source: {}
      )

      expect(workspace).not_to have_received(:write_subtitles)
      expect(result).to be_nil
    end
  end
end
