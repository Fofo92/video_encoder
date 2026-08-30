# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExporter, 'subtitle warnings' do
  let(:builder) { instance_double(VideoEncoder::MltProjectBuilder) }
  let(:renderer) { instance_double(VideoEncoder::MltRenderer) }
  let(:remuxer) { instance_double(VideoEncoder::FfmpegRemuxer) }
  let(:workspace) { instance_double(VideoEncoder::TrimWorkspace) }

  let(:subtitle_exporter) do
    instance_double(VideoEncoder::TrimSubtitleExporter)
  end

  let(:reporter) do
    instance_double(VideoEncoder::ExportProgressReporter)
  end

  let(:media) { instance_double(VideoEncoder::Media) }
  let(:video_track) { instance_double(VideoEncoder::VideoTrack) }
  let(:segment) { instance_double(VideoEncoder::Segment, source: media) }

  let(:project) do
    instance_double(VideoEncoder::TrimProject, segments: [segment])
  end

  it 'reports the missing group and stops before remuxing' do
    failure = VideoEncoder::TrimSubtitleExporter::IncompleteSubtitles.new(
      missing_groups: [1],
      subtitle_path: 'tmp/subtitles.srt'
    )

    allow(builder).to receive(:build).and_return('<mlt/>')

    allow(workspace).to receive_messages(
      write_mlt: nil,
      mlt_path: 'tmp/project.mlt',
      video_path: 'tmp/video.mkv'
    )

    allow(renderer).to receive(:render_video)
    allow(remuxer).to receive(:remux)
    allow(reporter).to receive(:call)
    allow(reporter).to receive(:warning)
    allow(subtitle_exporter).to receive(:call).and_raise(failure)

    exporter = described_class.new(
      builder: builder,
      renderer: renderer,
      remuxer: remuxer,
      workspace: workspace,
      subtitle_exporter: subtitle_exporter,
      progress_reporter: reporter
    )

    expect do
      exporter.call(
        trim_project: project,
        video_tracks_by_source: { media => video_track },
        audio_output_tracks: [],
        output_path: 'movie.mkv'
      )
    end.to raise_error(
      VideoEncoder::TrimSubtitleExporter::IncompleteSubtitles
    ) { |error|
      expect(error).to equal(failure)
    }

    expect(reporter).to have_received(:warning).with(
      code: 'no_subtitles_found',
      message: 'Aucun sous-titre trouvé pour le groupe 1.',
      group: 1
    ).once

    expect(remuxer).not_to have_received(:remux)
  end
end
