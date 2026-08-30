# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimSubtitleExporter, 'incomplete subtitles' do
  let(:processor) do
    instance_double(VideoEncoder::SubtitleProjectProcessor)
  end

  let(:composer) { instance_double(VideoEncoder::SrtComposer) }
  let(:workspace) { instance_double(VideoEncoder::TrimWorkspace) }

  let(:captioned_source) { instance_double(VideoEncoder::Media) }
  let(:uncaptioned_source) { instance_double(VideoEncoder::Media) }

  let(:video_track) do
    instance_double(
      VideoEncoder::VideoTrack,
      frame_rate: Rational(25, 1)
    )
  end

  let(:subtitle_track) { instance_double(VideoEncoder::Track) }

  let(:segments) do
    [
      [captioned_source, 0, 24],
      [uncaptioned_source, 0, 24],
      [captioned_source, 50, 74]
    ].map do |source, first, last|
      instance_double(
        VideoEncoder::Segment,
        source: source,
        start_frame: first,
        end_frame: last
      )
    end
  end

  let(:project) do
    instance_double(VideoEncoder::TrimProject, segments: segments)
  end

  before do
    allow(workspace).to receive(:subtitle_transport_path) do |index|
      "/tmp/subtitle_segment_#{index}.ts"
    end

    allow(workspace).to receive(:subtitle_manifest_path) do |index|
      "/tmp/subtitle_project_#{index}.ffconcat"
    end

    allow(workspace).to receive(:subtitle_project_transport_path) do |index|
      "/tmp/subtitle_project_#{index}.ts"
    end

    allow(workspace).to receive(:subtitle_project_srt_path) do |index|
      "/tmp/subtitle_project_#{index}.srt"
    end

    allow(workspace).to receive(:write_subtitles)
    allow(workspace).to receive(:subtitle_path)
      .and_return('/tmp/subtitles.srt')
  end

  it 'preserves valid subtitles before reporting the missing group' do
    exporter = described_class.new(
      processor: processor,
      composer: composer,
      workspace: workspace
    )

    allow(processor).to receive(:call) do |**arguments|
      if arguments.fetch(:timeline_start).zero?
        raise VideoEncoder::CcextractorOcr::NoSubtitlesFound,
              'No subtitles in the first group'
      end

      "valid subtitles at timeline position 2\n"
    end

    allow(composer).to receive(:call)
      .with(["valid subtitles at timeline position 2\n"])
      .and_return("composed valid subtitles\n")

    expect do
      exporter.call(
        trim_project: project,
        video_tracks_by_source: {
          captioned_source => video_track,
          uncaptioned_source => video_track
        },
        subtitle_tracks_by_source: {
          captioned_source => subtitle_track
        }
      )
    end.to raise_error(
      VideoEncoder::TrimSubtitleExporter::IncompleteSubtitles
    ) { |error|
      expect(error.missing_groups).to eq([1])
      expect(error.subtitle_path).to eq('/tmp/subtitles.srt')
    }

    expect(processor).to have_received(:call).twice

    expect(processor).to have_received(:call).with(
      hash_including(timeline_start: 2)
    )

    expect(workspace).to have_received(:write_subtitles)
      .with("composed valid subtitles\n")
  end

  it 'reports all missing groups without writing subtitles' do
    exporter = described_class.new(
      processor: processor,
      composer: composer,
      workspace: workspace
    )

    allow(processor).to receive(:call)
      .and_raise(
        VideoEncoder::CcextractorOcr::NoSubtitlesFound,
        'No subtitles'
      )

    allow(composer).to receive(:call)
      .with([])
      .and_return('')

    expect do
      exporter.call(
        trim_project: project,
        video_tracks_by_source: {
          captioned_source => video_track,
          uncaptioned_source => video_track
        },
        subtitle_tracks_by_source: {
          captioned_source => subtitle_track
        }
      )
    end.to raise_error(
      VideoEncoder::TrimSubtitleExporter::IncompleteSubtitles
    ) { |error|
      expect(error.missing_groups).to eq([1, 2])
      expect(error.subtitle_path).to be_nil
    }

    expect(processor).to have_received(:call).twice
    expect(workspace).not_to have_received(:write_subtitles)
  end

  it 'stops immediately on a technical failure' do
    exporter = described_class.new(
      processor: processor,
      composer: composer,
      workspace: workspace
    )

    failure = RuntimeError.new('technical failure')

    allow(processor).to receive(:call).and_raise(failure)
    allow(composer).to receive(:call)

    expect do
      exporter.call(
        trim_project: project,
        video_tracks_by_source: {
          captioned_source => video_track,
          uncaptioned_source => video_track
        },
        subtitle_tracks_by_source: {
          captioned_source => subtitle_track
        }
      )
    end.to raise_error(RuntimeError) { |error|
      expect(error).to equal(failure)
    }

    expect(processor).to have_received(:call).once
    expect(composer).not_to have_received(:call)
    expect(workspace).not_to have_received(:write_subtitles)
  end
end
