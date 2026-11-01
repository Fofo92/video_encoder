# frozen_string_literal: true

require 'spec_helper'

RSpec.describe 'Validated multilingual version' do
  let(:french) { VideoEncoder::Track.new(index: 1, type: :audio, language: 'fra') }
  let(:original) { VideoEncoder::Track.new(index: 2, type: :audio, language: 'qaa') }
  let(:subtitles) { VideoEncoder::Track.new(index: 3, type: :subtitle, language: 'fra') }
  let(:media) do
    VideoEncoder::Media.new(path: '/commun/film.m2t', duration: 100,
                            audio_tracks: [french, original], subtitle_tracks: [subtitles])
  end
  let(:project) do
    VideoEncoder::TrimProject.new.tap do |item|
      item.add_segment(VideoEncoder::Segment.new(source: media, start_frame: 0, end_frame: 100))
      item.track_selection = { 'mode' => 'original_without_subtitles' }
    end
  end

  it 'keeps both audio tracks without ordinary subtitles for VM' do
    exporter = double('exporter')
    expect(exporter).to receive(:call) do |**arguments|
      expect(arguments.fetch(:audio_output_tracks).map(&:role)).to eq(%i[french original])
      expect(arguments.fetch(:subtitle_tracks_by_source)).to eq({})
    end
    VideoEncoder::ExportTrimProject.new(selector: VideoEncoder::TrackSelector.new, exporter: exporter)
                                   .call(trim_project: project, output_path: 'film.mkv')
  end

  it 'does not run OCR or discard the original audio when VM has no subtitles' do
    exporter = double('subtitle exporter')
    expect(exporter).not_to receive(:call)
    tracks = VideoEncoder::TrackSelector.new.select_audio_outputs([media])
    result = VideoEncoder::SubtitleExportPreparation.new(exporter: exporter, progress_reporter: nil).call(
      trim_project: project, video_tracks_by_source: {}, subtitle_tracks_by_source: {},
      audio_output_tracks: tracks, rendered_video_path: 'video.mkv'
    )
    expect(result).to eq([nil, tracks])
  end

  it 'preserves original audio if forced subtitle extraction returns no text' do
    tracks = VideoEncoder::TrackSelector.new.select_audio_outputs([media])
    exporter = double('subtitle exporter', call: nil)
    result = VideoEncoder::SubtitleExportPreparation.new(exporter: exporter, progress_reporter: nil).call(
      trim_project: project, video_tracks_by_source: {}, subtitle_tracks_by_source: { media => subtitles },
      audio_output_tracks: tracks, rendered_video_path: 'video.mkv'
    )
    expect(result).to eq([nil, tracks])
  end

  it 'restores the VM policy and retains scope validation' do
    document = { 'format' => 'video_encoder.trim_project', 'version' => 2, 'project_id' => 'film',
                 'vidb' => { 'record_id' => 42 }, 'sources' => [{ 'id' => 'source', 'path' => '/commun/film.m2t' }],
                 'timeline' => [{ 'type' => 'segment', 'source_id' => 'source',
                                  'start_frame' => 0, 'end_frame' => 100 }],
                 'track_selection' => { 'mode' => 'original_without_subtitles',
                                        'scope' => { 'project_id' => 'film', 'record_id' => 42,
                                                     'source_paths' => ['/commun/film.m2t'] } } }
    loader = VideoEncoder::TrimProjectLoader.new(media_probe: double('probe', read: media))
    expect(loader.load(JSON.generate(document)).track_selection).to eq(document['track_selection'])
    document['vidb']['record_id'] = 43
    expect { loader.load(JSON.generate(document)) }.to raise_error(ArgumentError, /périmée/)
  end
end
