# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrackPreflightPlanner do
  let(:source) do
    instance_double(VideoEncoder::Media)
  end

  let(:video_track) do
    VideoEncoder::VideoTrack.new(
      index: 0,
      type: :video,
      frame_rate: Rational(25, 1)
    )
  end

  let(:french_track) do
    VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra'
    )
  end

  let(:original_track) do
    VideoEncoder::Track.new(
      index: 2,
      type: :audio,
      language: 'qaa'
    )
  end

  let(:subtitle_track) do
    VideoEncoder::Track.new(
      index: 3,
      type: :subtitle,
      language: 'fra'
    )
  end

  it 'plans one sample per selected track for a repeated source' do
    project = VideoEncoder::TrimProject.new

    [[0, 2999], [5000, 6999]].each do |first, last|
      project.add_segment(
        VideoEncoder::Segment.new(
          source: source,
          start_frame: first,
          end_frame: last
        )
      )
    end

    audio_outputs = [
      VideoEncoder::AudioOutputTrack.new(
        role: :french,
        tracks_by_source: { source => french_track }
      ),
      VideoEncoder::AudioOutputTrack.new(
        role: :original,
        tracks_by_source: { source => original_track }
      )
    ]

    samples = described_class.new(sample_seconds: 60).call(
      trim_project: project,
      video_tracks_by_source: { source => video_track },
      audio_output_tracks: audio_outputs,
      subtitle_tracks_by_source: { source => subtitle_track }
    )

    expect(samples).to eq(
      [french_track, original_track, subtitle_track].map do |track|
        {
          source: source,
          track: track,
          start_frame: 750,
          end_frame: 2249,
          frame_rate: Rational(25, 1)
        }
      end
    )
  end
  it 'plans independent samples for each source' do
    other_source = instance_double(VideoEncoder::Media)

    other_video = VideoEncoder::VideoTrack.new(
      index: 0,
      type: :video,
      frame_rate: Rational(50, 1)
    )

    other_audio = VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra'
    )

    project = VideoEncoder::TrimProject.new

    [
      [source, 0, 2999],
      [other_source, 10_000, 15_999],
      [source, 5000, 6999]
    ].each do |media, first, last|
      project.add_segment(
        VideoEncoder::Segment.new(
          source: media,
          start_frame: first,
          end_frame: last
        )
      )
    end

    audio_output = VideoEncoder::AudioOutputTrack.new(
      role: :french,
      tracks_by_source: {
        source => french_track,
        other_source => other_audio
      }
    )

    samples = described_class.new(sample_seconds: 60).call(
      trim_project: project,
      video_tracks_by_source: {
        source => video_track,
        other_source => other_video
      },
      audio_output_tracks: [audio_output],
      subtitle_tracks_by_source: {}
    )

    expect(samples).to eq(
      [
        {
          source: source,
          track: french_track,
          start_frame: 750,
          end_frame: 2249,
          frame_rate: Rational(25, 1)
        },
        {
          source: other_source,
          track: other_audio,
          start_frame: 11_500,
          end_frame: 14_499,
          frame_rate: Rational(50, 1)
        }
      ]
    )
  end

  it 'uses the whole segment when it is shorter than the sample duration' do
    project = VideoEncoder::TrimProject.new

    project.add_segment(
      VideoEncoder::Segment.new(
        source: source,
        start_frame: 100,
        end_frame: 349
      )
    )

    samples = described_class.new(sample_seconds: 60).call(
      trim_project: project,
      video_tracks_by_source: { source => video_track },
      audio_output_tracks: [],
      subtitle_tracks_by_source: { source => subtitle_track }
    )

    expect(samples).to eq(
      [
        {
          source: source,
          track: subtitle_track,
          start_frame: 100,
          end_frame: 349,
          frame_rate: Rational(25, 1)
        }
      ]
    )
  end
end
