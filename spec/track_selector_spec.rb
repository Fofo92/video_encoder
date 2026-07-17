# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrackSelector do
  subject(:selector) { described_class.new }

  let(:video) do
    VideoEncoder::Track.new(
      index: 0,
      type: :video,
      codec: 'h264'
    )
  end

  let(:french_audio) do
    VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra',
      codec: 'eac3'
    )
  end

  let(:descriptive_audio) do
    VideoEncoder::Track.new(
      index: 2,
      type: :audio,
      language: 'qaa',
      codec: 'eac3',
      visual_impaired: true
    )
  end

  let(:german_audio) do
    VideoEncoder::Track.new(
      index: 3,
      type: :audio,
      language: 'deu',
      codec: 'eac3'
    )
  end

  let(:french_subtitle) do
    VideoEncoder::Track.new(
      index: 4,
      type: :subtitle,
      language: 'fra',
      codec: 'dvb_subtitle'
    )
  end

  let(:hearing_impaired_subtitle) do
    VideoEncoder::Track.new(
      index: 5,
      type: :subtitle,
      language: 'fra',
      codec: 'dvb_subtitle',
      hearing_impaired: true
    )
  end

  let(:media) do
    VideoEncoder::Media.new(
      duration: 100,
      video_tracks: [video],
      audio_tracks: [
        french_audio,
        descriptive_audio,
        german_audio
      ],
      subtitle_tracks: [
        french_subtitle,
        hearing_impaired_subtitle
      ]
    )
  end

  it 'selects the first video track' do
    expect(selector.select(media)[:video]).to eq(video)
  end

  it 'selects French and original audio tracks' do
    expect(selector.select(media)[:audio])
      .to eq([french_audio, german_audio])
  end

  it 'ignores descriptive audio' do
    expect(selector.select(media)[:audio])
      .not_to include(descriptive_audio)
  end

  it 'selects standard French subtitles for foreign audio' do
    expect(selector.select(media)[:subtitles])
      .to eq([french_subtitle])
  end
  it 'returns the selected track indexes' do
    selection = selector.select(media)

    expect(selection[:video].index).to eq(0)
    expect(selection[:audio].map(&:index)).to eq([1, 3])
    expect(selection[:subtitles].map(&:index)).to eq([4])
  end

  it 'ignores qaa audio tracks' do
    qaa_audio = VideoEncoder::Track.new(
      index: 2,
      type: :audio,
      language: 'qaa',
      codec: 'eac3'
    )

    media_with_qaa = VideoEncoder::Media.new(
      duration: 100,
      video_tracks: [video],
      audio_tracks: [
        french_audio,
        qaa_audio,
        german_audio
      ],
      subtitle_tracks: [french_subtitle]
    )

    expect(selector.select(media_with_qaa)[:audio])
      .to eq([french_audio, german_audio])
  end
end
