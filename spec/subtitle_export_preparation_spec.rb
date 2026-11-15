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
      audio_output_tracks: [],
      rendered_video_path: 'tmp/video.mkv'
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
        audio_output_tracks: [],
        rendered_video_path: 'tmp/video.mkv'
      )
    end.to raise_error(
      VideoEncoder::CcextractorOcr::TechnicalFailure
    ) { |error|
      expect(error).to equal(technical_failure)
    }
  end

  context 'when VMST is explicitly selected' do
    let(:project) { double('project', track_selection: { 'mode' => 'original_with_subtitles' }) }
    let(:french) { double('audio output', role: :french) }
    let(:original) { double('audio output', role: :original) }

    def prepare_selected
      preparation.call(
        trim_project: project,
        video_tracks_by_source: { source => :video_track },
        subtitle_tracks_by_source: { source => normal_track },
        audio_output_tracks: [french, original],
        rendered_video_path: 'tmp/video.mkv'
      )
    end

    def prepare_without_selected_subtitles
      preparation.call(
        trim_project: project,
        video_tracks_by_source: { source => :video_track },
        subtitle_tracks_by_source: {},
        audio_output_tracks: [french, original],
        rendered_video_path: 'tmp/video.mkv'
      )
    end

    it 'warns and keeps French and original audio when the source has no subtitle tracks' do
      allow(source).to receive(:subtitle_tracks).and_return([])
      expect(exporter).not_to receive(:call)
      expect(prepare_without_selected_subtitles).to eq([nil, [french, original]])
      expect(reporter).to have_received(:warning).with(hash_including(code: 'vmst_without_subtitle_tracks'))
    end

    it 'does not mistake filtered subtitle tracks for an absence of tracks in the source' do
      allow(source).to receive(:subtitle_tracks).and_return([hearing_impaired_track])
      allow(exporter).to receive(:call).and_return(nil)
      expect(prepare_without_selected_subtitles).to eq([nil, [french, original]])
      expect(reporter).not_to have_received(:warning).with(hash_including(code: 'vmst_without_subtitle_tracks'))
    end

    it 'does not drop available subtitles just because another source has no track' do
      empty_source = instance_double(VideoEncoder::Media, subtitle_tracks: [])
      allow(exporter).to receive(:call).and_return('tmp/subtitles.srt')
      result = preparation.call(
        trim_project: project,
        video_tracks_by_source: { source => :video_track, empty_source => :other_video },
        subtitle_tracks_by_source: { source => normal_track },
        audio_output_tracks: [french, original],
        rendered_video_path: 'tmp/video.mkv'
      )
      expect(result).to eq(['tmp/subtitles.srt', [french, original]])
    end

    it 'warns and keeps both audio tracks when the subtitle export returns no text' do
      allow(exporter).to receive(:call).and_return(nil)
      expect(prepare_selected).to eq([nil, [french, original]])
      expect(reporter).to have_received(:warning).with(hash_including(code: 'vmst_without_subtitle_text'))
      expect(reporter).not_to have_received(:warning).with(hash_including(code: 'original_audio_omitted_no_subtitles'))
    end

    it 'keeps both audio tracks with a warning when all subtitle groups contain no text' do
      failure = VideoEncoder::TrimSubtitleExporter::IncompleteSubtitles.new(missing_groups: [1], subtitle_path: nil)
      allow(exporter).to receive(:call).and_raise(failure)
      expect(prepare_selected).to eq([nil, [french, original]])
      expect(reporter).to have_received(:warning).with(hash_including(code: 'vmst_without_subtitle_text'))
    end

    it 'still propagates technical failures rather than treating them as an empty subtitle track' do
      allow(exporter).to receive(:call).and_raise(technical_failure)
      expect { prepare_selected }.to raise_error(VideoEncoder::CcextractorOcr::TechnicalFailure)
    end

    it 'still rejects partial subtitles rather than declaring a complete export' do
      failure = VideoEncoder::TrimSubtitleExporter::IncompleteSubtitles.new(
        missing_groups: [2], subtitle_path: 'tmp/partial.srt'
      )
      allow(exporter).to receive(:call).and_raise(failure)
      expect { prepare_selected }.to raise_error(VideoEncoder::TrimSubtitleExporter::IncompleteSubtitles)
    end

    it 'retains both audio tracks when subtitles are available' do
      allow(exporter).to receive(:call).and_return('tmp/subtitles.srt')
      expect(prepare_selected).to eq(['tmp/subtitles.srt', [french, original]])
    end

    it 'rejects a missing subtitle exporter for a VMST request' do
      service = described_class.new(exporter: nil, progress_reporter: reporter)
      expect do
        service.call(trim_project: project, video_tracks_by_source: {}, subtitle_tracks_by_source: {},
                     audio_output_tracks: [french, original], rendered_video_path: 'tmp/video.mkv')
      end.to raise_error(described_class::RequiredSubtitlesUnavailable)
    end
  end
end
