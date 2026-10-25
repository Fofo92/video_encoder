# frozen_string_literal: true

require 'spec_helper'
require 'rexml'

RSpec.describe VideoEncoder::MltProjectBuilder do
  subject(:builder) { described_class.new }

  let(:sources) do
    %w[/media/a.m2t /media/b.m2t].map do |path|
      instance_double(VideoEncoder::Media, path: Pathname(path))
    end
  end

  let(:video_tracks) do
    {
      sources[0] => instance_double(VideoEncoder::VideoTrack, index: 0, frame_rate: Rational(50, 1)),
      sources[1] => instance_double(VideoEncoder::VideoTrack, index: 2, frame_rate: Rational(25, 1))
    }
  end

  let(:audio_tracks) do
    {
      sources[0] => instance_double(VideoEncoder::Track, index: 1),
      sources[1] => instance_double(VideoEncoder::Track, index: 3)
    }
  end

  let(:project) do
    VideoEncoder::TrimProject.new.tap do |trim_project|
      trim_project.add_segment(
        VideoEncoder::Segment.new(source: sources[0], start_frame: 101, end_frame: 198)
      )
      trim_project.add_segment(
        VideoEncoder::Segment.new(source: sources[1], start_frame: 400, end_frame: 449)
      )
    end
  end

  def document_for(**options)
    REXML::Document.new(
      builder.build(
        project,
        video_tracks_by_source: video_tracks,
        audio_tracks_by_source: audio_tracks,
        **options
      )
    )
  end

  def stream_indices(document, name)
    document.get_elements("mlt/chain/property[@name='#{name}']").map(&:text)
  end

  def boundaries(document)
    document.get_elements('mlt/playlist/entry').map do |entry|
      [entry.attributes['in'], entry.attributes['out']]
    end
  end

  it 'keeps video disabled in every audio producer despite the video metadata map' do
    document = document_for(video_index: -1)

    expect(stream_indices(document, 'video_index')).to eq(%w[-1 -1])
    expect(stream_indices(document, 'audio_index')).to eq(%w[1 3])
    expect(boundaries(document)).to eq([%w[50 99], %w[400 449]])
    expect(boundaries(document)).to eq(boundaries(document_for(audio_index: -1)))
  end

  it 'keeps audio disabled when an audio track map is also supplied' do
    document = document_for(audio_index: -1)

    expect(stream_indices(document, 'audio_index')).to eq(%w[-1 -1])
    expect(stream_indices(document, 'video_index')).to eq(%w[0 2])
  end

  it 'still selects source-specific streams when neither stream is disabled' do
    document = document_for

    expect(stream_indices(document, 'video_index')).to eq(%w[0 2])
    expect(stream_indices(document, 'audio_index')).to eq(%w[1 3])
  end
end
