# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ExportTrimProject do
  subject(:service) do
    described_class.new(
      selector: selector,
      exporter: exporter
    )
  end

  let(:selector) { instance_double(VideoEncoder::TrackSelector) }
  let(:exporter) { instance_double(VideoEncoder::TrimExporter) }

  describe '#call' do
    it 'selects project tracks and exports the trimmed media' do
      media_a = instance_double(VideoEncoder::Media)
      media_c = instance_double(VideoEncoder::Media)

      segment_a = instance_double(
        VideoEncoder::Segment,
        source: media_a
      )

      segment_c = instance_double(
        VideoEncoder::Segment,
        source: media_c
      )

      project = instance_double(
        VideoEncoder::TrimProject,
        segments: [segment_a, segment_c, segment_a]
      )

      video_tracks = { media_a => :video_a, media_c => :video_c }
      audio_outputs = %i[french original]
      subtitle_tracks = { media_c => :french_subtitles }

      allow(selector).to receive(:select_video_tracks)
        .with([media_a, media_c])
        .and_return(video_tracks)

      allow(selector).to receive(:select_audio_outputs)
        .with([media_a, media_c])
        .and_return(audio_outputs)

      allow(selector).to receive(:select_subtitle_tracks)
        .with([media_a, media_c])
        .and_return(subtitle_tracks)

      allow(exporter).to receive(:call)
        .and_return('/output/movie.mkv')

      result = service.call(
        trim_project: project,
        output_path: '/output/movie.mkv'
      )

      expect(exporter).to have_received(:call).with(
        trim_project: project,
        video_tracks_by_source: video_tracks,
        audio_output_tracks: audio_outputs,
        subtitle_tracks_by_source: subtitle_tracks,
        output_path: '/output/movie.mkv'
      )

      expect(result).to eq('/output/movie.mkv')
    end
  end
end
