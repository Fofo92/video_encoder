# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleExportPreparation do
  subject(:preparation) do
    described_class.new(
      exporter: exporter,
      progress_reporter: reporter
    )
  end

  let(:exporter) do
    instance_double(VideoEncoder::TrimSubtitleExporter)
  end

  let(:reporter) do
    instance_double(VideoEncoder::ExportProgressReporter)
  end

  let(:normal_track) do
    instance_double(
      VideoEncoder::Track,
      index: 5,
      language: 'fra',
      hearing_impaired: false
    )
  end

  let(:hearing_impaired_track) do
    instance_double(
      VideoEncoder::Track,
      index: 4,
      language: 'fra',
      hearing_impaired: true
    )
  end

  let(:source) do
    instance_double(
      VideoEncoder::Media,
      subtitle_tracks: [
        normal_track,
        hearing_impaired_track
      ]
    )
  end

  let(:technical_failure) do
    failure = instance_double(
      VideoEncoder::CommandRunner::CommandFailed,
      message: 'CCExtractor failed'
    )

    VideoEncoder::CcextractorOcr::TechnicalFailure.new(
      failure
    )
  end

  before do
    allow(reporter).to receive(:call)
    allow(reporter).to receive(:warning)
  end

  it 'retries with hearing-impaired subtitles after a technical failure' do
    attempted_tracks = []

    allow(exporter).to receive(:call) do |subtitle_tracks_by_source:, **|
      selected = subtitle_tracks_by_source.fetch(source)
      attempted_tracks << selected

      raise technical_failure if selected == normal_track

      'tmp/subtitles.srt'
    end

    result = preparation.call(
      trim_project: :project,
      video_tracks_by_source: { source => :video_track },
      subtitle_tracks_by_source: {
        source => normal_track
      },
      audio_output_tracks: []
    )

    expect(result).to eq(
      ['tmp/subtitles.srt', []]
    )
    expect(attempted_tracks).to eq(
      [normal_track, hearing_impaired_track]
    )
    expect(reporter).to have_received(:warning).with(
      code: 'hearing_impaired_subtitles_fallback',
      message: 'La piste de sous-titres normale est inutilisable : utilisation de la piste pour malentendants.'
    ).once
  end

  it 'preserves the failure when no fallback track exists' do
    allow(source).to receive(:subtitle_tracks)
      .and_return([normal_track])
    allow(exporter).to receive(:call)
      .and_raise(technical_failure)

    expect do
      preparation.call(
        trim_project: :project,
        video_tracks_by_source: {
          source => :video_track
        },
        subtitle_tracks_by_source: {
          source => normal_track
        },
        audio_output_tracks: []
      )
    end.to raise_error(
      VideoEncoder::CcextractorOcr::TechnicalFailure
    ) { |error|
      expect(error).to equal(technical_failure)
    }
  end
end
