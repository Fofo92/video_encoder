# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExporter, 'French original progress' do
  let(:media) { VideoEncoder::Media.new(path: '/commun/film.m2t', duration: 100) }
  let(:project) do
    VideoEncoder::TrimProject.new.tap do |item|
      item.add_segment(VideoEncoder::Segment.new(source: media, start_frame: 0, end_frame: 100))
      item.track_selection = { 'mode' => 'french_only' }
    end
  end
  let(:audio) { VideoEncoder::AudioOutputTrack.new(role: :french, tracks_by_source: { media => :french }) }
  let(:events) { [] }
  let(:subtitles) { double('subtitle exporter') }
  let(:renderer) { double('renderer', render_video: nil, render_audio: nil) }
  let(:remuxer) { double('remuxer', remux: nil) }
  let(:workspace) do
    double('workspace', write_mlt: nil, mlt_path: 'video.mlt', video_path: 'video.mkv',
                        write_audio_mlt: 'audio.mlt', audio_path: 'audio.mka')
  end
  let(:exporter) do
    described_class.new(builder: double('builder', build: '<mlt/>'), renderer: renderer, remuxer: remuxer,
                        workspace: workspace, subtitle_exporter: subtitles,
                        progress_reporter: ->(**event) { events << event })
  end

  it 'reports three consecutive stages and never invokes OCR when French-only was explicitly chosen' do
    expect(subtitles).not_to receive(:call)
    exporter.call(trim_project: project, video_tracks_by_source: {}, audio_output_tracks: [audio],
                  output_path: 'film.mkv')
    expect(events).to eq([
                           { stage: :video, step: 1, total: 3 },
                           { stage: :audio, step: 2, total: 3, track: 1, tracks: 1, role: :french },
                           { stage: :remux, step: 3, total: 3 }
                         ])
  end

  it 'retains the subtitle stage for selected forced subtitles' do
    expect(subtitles).to receive(:call).with(hash_including(subtitle_tracks_by_source: { media => :forced }))
                                       .and_return('forced.srt')
    exporter.call(trim_project: project, video_tracks_by_source: {}, audio_output_tracks: [audio],
                  subtitle_tracks_by_source: { media => :forced }, output_path: 'film.mkv')
    expect(events.map { |event| event.fetch(:stage) }).to eq(%i[video subtitles audio remux])
    expect(events.map { |event| event.fetch(:step) }).to eq([1, 2, 3, 4])
    expect(events.map { |event| event.fetch(:total) }.uniq).to eq([4])
    expect(remuxer).to have_received(:remux).with(hash_including(subtitle_path: 'forced.srt'))
  end
end
