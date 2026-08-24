# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SrtNormalizer do
  describe '#call' do
    it 'removes font tags from subtitle text' do
      srt = <<~SRT
        1
        00:00:00,320 --> 00:00:01,399
        <font color="#ffffff">À vos ordres !</font>

      SRT

      normalized = described_class.new.call(srt)

      expect(normalized).to include('À vos ordres !')
      expect(normalized).not_to include('<font')
      expect(normalized).not_to include('</font>')
    end

    it 'shifts subtitle timestamps by the configured offset' do
      srt = <<~SRT
        1
        00:00:00,320 --> 00:00:01,399
        À vos ordres !

      SRT

      normalized = described_class.new.call(
        srt,
        offset: 60.65
      )

      expect(normalized).to include(
        '00:01:00,970 --> 00:01:02,049'
      )
    end
  end

  it 'clips a subtitle at the end of its output segment' do
    srt = <<~SRT
      24
      00:00:58,640 --> 00:01:01,000
      J'aurais dû la virer hier.

    SRT

    normalized = described_class.new.call(
      srt,
      offset: 60.65,
      end_at: 120
    )

    expect(normalized).to include(
      '00:01:59,290 --> 00:02:00,000'
    )
  end

  it 'clips subtitles at the beginning of their output segment' do
    srt = <<~SRT
      1
      00:19:50,000 --> 00:19:51,000
      Sous-titre antérieur.

      2
      00:19:58,000 --> 00:20:01,000
      Sous-titre à cheval sur le raccord.

      3
      00:20:02,860 --> 00:20:06,299
      Sous-titre dans le segment.

    SRT

    normalized = described_class.new.call(
      srt,
      offset: -1_200,
      start_at: 0,
      end_at: 60
    )

    expect(normalized).not_to include('Sous-titre antérieur.')

    expect(normalized).to include(
      '00:00:00,000 --> 00:00:01,000'
    )

    expect(normalized).to include(
      '00:00:02,860 --> 00:00:06,299'
    )
  end

  it 'rejects subtitle entries with a non-positive duration' do
    srt = <<~SRT
      23
      00:00:55,360 --> 00:00:58,439
      Sous-titre valide.

      24
      00:00:58,640 --> 00:00:58,639
      Sous-titre invalide.

    SRT

    normalized = described_class.new.call(srt)

    expect(normalized).to include('Sous-titre valide.')
    expect(normalized).not_to include('Sous-titre invalide.')
  end
end
