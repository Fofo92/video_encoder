# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CheckTrimProjectAudio do
  it 'does not analyze an audio track confirmed for its source' do
    source = instance_double(VideoEncoder::Media)
    video = VideoEncoder::VideoTrack.new(
      index: 0,
      type: :video,
      frame_rate: Rational(25, 1)
    )
    audio = VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra'
    )

    project = VideoEncoder::TrimProject.new
    project.add_segment(
      VideoEncoder::Segment.new(
        source: source,
        start_frame: 0,
        end_frame: 2999
      )
    )

    audio_output = VideoEncoder::AudioOutputTrack.new(
      role: :french,
      tracks_by_source: { source => audio }
    )

    selector = instance_double(VideoEncoder::TrackSelector)
    allow(selector).to receive(:select_video_tracks)
      .with([source])
      .and_return({ source => video })
    allow(selector).to receive(:select_audio_outputs)
      .with([source])
      .and_return([audio_output])

    analyzer = instance_double(VideoEncoder::AudioSampleAnalyzer)
    allow(analyzer).to receive(:call)

    service = described_class.new(
      selector: selector,
      planner: VideoEncoder::TrackPreflightPlanner.new,
      checker: VideoEncoder::AudioPreflightChecker.new(
        analyzer: analyzer
      )
    )

    results = service.call(
      trim_project: project,
      confirmed_audio_tracks_by_source: {
        source => [audio.index]
      }
    )

    expect(results).to eq([])
    expect(analyzer).not_to have_received(:call)
  end

  it 'analyzes an unconfirmed audio track and returns its result' do
    source = instance_double(VideoEncoder::Media)
    video = VideoEncoder::VideoTrack.new(
      index: 0,
      type: :video,
      frame_rate: Rational(25, 1)
    )
    audio = VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra'
    )

    project = VideoEncoder::TrimProject.new
    project.add_segment(
      VideoEncoder::Segment.new(
        source: source,
        start_frame: 0,
        end_frame: 2999
      )
    )

    audio_output = VideoEncoder::AudioOutputTrack.new(
      role: :french,
      tracks_by_source: { source => audio }
    )

    selector = instance_double(VideoEncoder::TrackSelector)
    allow(selector).to receive(:select_video_tracks)
      .with([source])
      .and_return({ source => video })
    allow(selector).to receive(:select_audio_outputs)
      .with([source])
      .and_return([audio_output])

    sample = {
      source: source,
      track: audio,
      start_frame: 750,
      end_frame: 2249,
      frame_rate: Rational(25, 1)
    }
    analysis = {
      status: :signal_detected,
      sample_count: 2_880_000,
      mean_volume_db: -25.0,
      max_volume_db: -3.0
    }

    analyzer = instance_double(VideoEncoder::AudioSampleAnalyzer)
    allow(analyzer).to receive(:call)
      .with(sample)
      .and_return(analysis)

    service = described_class.new(
      selector: selector,
      planner: VideoEncoder::TrackPreflightPlanner.new,
      checker: VideoEncoder::AudioPreflightChecker.new(
        analyzer: analyzer
      )
    )

    results = service.call(trim_project: project)

    expect(results).to eq([sample.merge(analysis: analysis)])
    expect(analyzer).to have_received(:call).with(sample).once
  end
end
