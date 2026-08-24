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

  let(:accessibility_audio) do
    VideoEncoder::Track.new(
      index: 2,
      type: :audio,
      language: 'fra',
      codec: 'eac3',
      visual_impaired: true
    )
  end

  let(:original_audio) do
    VideoEncoder::Track.new(
      index: 3,
      type: :audio,
      language: 'qaa',
      codec: 'eac3'
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
      path: 'movie.mkv', duration: 100,
      video_tracks: [video],
      audio_tracks: [
        french_audio,
        accessibility_audio,
        original_audio
      ],
      subtitle_tracks: [
        french_subtitle,
        hearing_impaired_subtitle
      ]
    )
  end

  describe '#select' do
    it 'selects the first video track' do
      expect(selector.select(media)[:video]).to eq(video)
    end

    it 'selects French and original-version audio tracks' do
      expect(selector.select(media)[:audio])
        .to eq([french_audio, original_audio])
    end

    it 'ignores accessibility audio tracks' do
      expect(selector.select(media)[:audio])
        .not_to include(accessibility_audio)
    end

    it 'selects standard French subtitles when original audio is kept' do
      expect(selector.select(media)[:subtitles])
        .to eq([french_subtitle])
    end

    it 'ignores hearing impaired subtitles' do
      expect(selector.select(media)[:subtitles])
        .not_to include(hearing_impaired_subtitle)
    end
  end

  context 'when another foreign-language track is present' do
    let(:german_audio) do
      VideoEncoder::Track.new(index: 4, type: :audio, language: 'deu', codec: 'eac3')
    end

    let(:media) do
      VideoEncoder::Media.new(
        path: 'movie.mkv', duration: 100,
        video_tracks: [video],
        audio_tracks: [french_audio, accessibility_audio, original_audio, german_audio],
        subtitle_tracks: [french_subtitle]
      )
    end

    it 'keeps the original-version audio instead of another foreign-language track' do
      expect(selector.select(media)[:audio])
        .to eq([french_audio, original_audio])
    end
  end

  context 'when no original-version audio track is available' do
    let(:media) do
      VideoEncoder::Media.new(
        path: 'movie.mkv',
        duration: 100, video_tracks: [video],
        audio_tracks: [
          french_audio, accessibility_audio
        ],
        subtitle_tracks: [
          french_subtitle, hearing_impaired_subtitle
        ]
      )
    end

    it 'selects only the French audio track' do
      expect(selector.select(media)[:audio])
        .to eq([french_audio])
    end

    context 'when several foreign-language audio tracks are available' do
      let(:german_audio) do
        VideoEncoder::Track.new(index: 4, type: :audio, language: 'deu', codec: 'eac3')
      end

      let(:media) do
        VideoEncoder::Media.new(
          path: 'movie.mkv',
          duration: 100, video_tracks: [video],
          audio_tracks: [french_audio, accessibility_audio, original_audio, german_audio],
          subtitle_tracks: [french_subtitle]
        )
      end

      it 'selects only the original-version audio track' do
        expect(selector.select(media)[:audio])
          .to eq([french_audio, original_audio])
      end
    end

    context 'when several French audio tracks are available' do
      let(:second_french_audio) do
        VideoEncoder::Track.new(index: 4, type: :audio, language: 'fra', codec: 'aac')
      end

      let(:media) do
        VideoEncoder::Media.new(
          path: 'movie.mkv', duration: 100,
          video_tracks: [video],
          audio_tracks: [french_audio, second_french_audio, original_audio],
          subtitle_tracks: [french_subtitle]
        )
      end

      it 'selects the first French audio track' do
        expect(selector.select(media)[:audio])
          .to eq([french_audio, original_audio])
      end
    end

    it 'does not select subtitles' do
      expect(selector.select(media)[:subtitles])
        .to eq([])
    end
  end

  describe '#select_subtitle_tracks' do
    it 'selects standard French subtitles only from eligible sources' do
      french_audio = instance_double(VideoEncoder::Track, language: 'fra', visual_impaired: false)

      original_audio = instance_double(VideoEncoder::Track, language: 'qaa', visual_impaired: false)

      standard_subtitle = instance_double(
        VideoEncoder::Track, language: 'fra', hearing_impaired: false
      )

      hearing_impaired_subtitle = instance_double(
        VideoEncoder::Track, language: 'fra', hearing_impaired: true
      )

      media_with_subtitles = instance_double(
        VideoEncoder::Media,
        audio_tracks: [french_audio, original_audio],
        subtitle_tracks: [hearing_impaired_subtitle, standard_subtitle]
      )

      media_without_subtitles = instance_double(
        VideoEncoder::Media,
        audio_tracks: [french_audio, original_audio],
        subtitle_tracks: [hearing_impaired_subtitle]
      )

      expect(
        selector.select_subtitle_tracks(
          [media_with_subtitles, media_without_subtitles]
        )
      ).to eq(
        media_with_subtitles => standard_subtitle
      )
    end
  end
end
