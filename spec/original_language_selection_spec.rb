# frozen_string_literal: true

require 'spec_helper'
require 'json'

RSpec.describe 'Original language track selection' do
  let(:french) { VideoEncoder::Track.new(index: 1, type: :audio, language: 'fra') }
  let(:original) { VideoEncoder::Track.new(index: 2, type: :audio, language: 'qaa') }
  let(:description) { VideoEncoder::Track.new(index: 3, type: :audio, language: 'fra', visual_impaired: true) }
  let(:captions) { VideoEncoder::Track.new(index: 4, type: :subtitle, language: 'fra', hearing_impaired: true) }
  let(:subtitles) { VideoEncoder::Track.new(index: 5, type: :subtitle, language: 'fra') }
  let(:media) do
    VideoEncoder::Media.new(path: '/commun/film.m2t', duration: 100,
                            audio_tracks: [french, original, description], subtitle_tracks: [captions, subtitles])
  end
  let(:project) do
    VideoEncoder::TrimProject.new.tap do |item|
      item.add_segment(VideoEncoder::Segment.new(source: media, start_frame: 0, end_frame: 100))
      item.track_selection = { 'mode' => 'french_only' }
    end
  end

  it 'selects only French audio, excluding qaa and audiodescription' do
    tracks = VideoEncoder::TrackSelector.new(french_only: true).select_audio_outputs([media])
    expect(tracks.map(&:role)).to eq([:french])
    expect(tracks.first.track_for(media)).to eq(french)
  end

  it 'selects no ordinary or hearing-impaired subtitles for a French original' do
    expect(VideoEncoder::TrackSelector.new(french_only: true).select_subtitle_tracks([media])).to eq({})
  end

  it 'preserves explicitly forced French subtitles' do
    forced = VideoEncoder::Track.new(index: 6, type: :subtitle, language: 'fra', forced: true)
    media.subtitle_tracks << forced
    expect(VideoEncoder::TrackSelector.new(french_only: true).select_subtitle_tracks([media])).to eq(media => forced)
  end

  it 'keeps the existing two-audio-track and ordinary-subtitle route for a foreign original' do
    selector = VideoEncoder::TrackSelector.new
    expect(selector.select_audio_outputs([media]).map(&:role)).to eq(%i[french original])
    expect(selector.select_subtitle_tracks([media])).to eq(media => subtitles)
  end

  it 'does not silently fall back to qaa when French is missing from one source' do
    other = VideoEncoder::Media.new(path: '/commun/other.m2t', duration: 100, audio_tracks: [original])
    expect do
      VideoEncoder::TrackSelector.new(french_only: true).select_audio_outputs([media, other])
    end.to raise_error(ArgumentError, /française/)
  end

  it 'skips the subtitle exporter and its progress stage entirely when no subtitle is selected' do
    exporter = double('subtitle exporter')
    reporter = double('progress reporter')
    tracks = VideoEncoder::TrackSelector.new(french_only: true).select_audio_outputs([media])
    preparation = VideoEncoder::SubtitleExportPreparation.new(exporter: exporter, progress_reporter: reporter)
    expect(exporter).not_to receive(:call)
    expect(reporter).not_to receive(:call)
    expect(preparation.call(trim_project: project, video_tracks_by_source: {}, subtitle_tracks_by_source: {},
                            audio_output_tracks: tracks, rendered_video_path: 'video.mkv')).to eq([nil, tracks])
  end

  it 'applies French-only selection before audio preflight' do
    planner = double('planner')
    checker = double('checker')
    expect(planner).to receive(:call) do |**arguments|
      expect(arguments.fetch(:audio_output_tracks).map(&:role)).to eq([:french])
      []
    end
    expect(checker).to receive(:call).with([])
    VideoEncoder::CheckTrimProjectAudio.new(selector: VideoEncoder::TrackSelector.new, planner: planner,
                                            checker: checker).call(trim_project: project)
  end

  it 'applies the same selection before export' do
    exporter = double('exporter')
    expect(exporter).to receive(:call) do |**arguments|
      expect(arguments.fetch(:audio_output_tracks).map(&:role)).to eq([:french])
      expect(arguments.fetch(:subtitle_tracks_by_source)).to eq({})
    end
    VideoEncoder::ExportTrimProject.new(selector: VideoEncoder::TrackSelector.new, exporter: exporter)
                                   .call(trim_project: project, output_path: 'film.mkv')
  end

  describe 'project restoration' do
    let(:document) do
      { 'format' => 'video_encoder.trim_project', 'version' => 2, 'project_id' => 'film',
        'vidb' => { 'record_id' => 42 }, 'sources' => [{ 'id' => 'source', 'path' => '/commun/film.m2t' }],
        'timeline' => [{ 'type' => 'segment', 'source_id' => 'source', 'start_frame' => 0, 'end_frame' => 100 }],
        'track_selection' => { 'mode' => 'french_only', 'scope' => { 'project_id' => 'film', 'record_id' => 42,
                                                                     'source_paths' => ['/commun/film.m2t'] } } }
    end
    let(:loader) { VideoEncoder::TrimProjectLoader.new(media_probe: double('probe', read: media)) }

    it 'restores the persisted selection' do
      expect(loader.load(JSON.generate(document)).track_selection).to eq(document['track_selection'])
    end

    it 'rejects a selection referring to another work' do
      document['vidb']['record_id'] = 43
      expect { loader.load(JSON.generate(document)) }.to raise_error(ArgumentError, /périmée/)
    end

    it 'rejects a selection referring to another source' do
      document['sources'].first['path'] = '/commun/other.m2t'
      expect { loader.load(JSON.generate(document)) }.to raise_error(ArgumentError, /périmée/)
    end

    it 'keeps older projects compatible without a selection' do
      document.delete('track_selection')
      expect(loader.load(JSON.generate(document)).track_selection).to be_nil
    end
  end
end
