# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleTimelineNormalizer do
  it 'normalizes each segment with its own correction' do
    normalizer = instance_double(
      VideoEncoder::SrtNormalizer
    )

    composer = instance_double(
      VideoEncoder::SrtComposer
    )

    raw_srt = "raw subtitles\n"

    allow(normalizer)
      .to receive(:call)
      .and_return(
        "first segment\n",
        "second segment\n"
      )

    allow(composer)
      .to receive(:call)
      .with(
        [
          "first segment\n",
          "second segment\n"
        ]
      )
      .and_return("composed subtitles\n")

    result = described_class.new(
      normalizer: normalizer,
      composer: composer
    ).call(
      raw_srt,
      timeline_start: 120,
      segments: [
        {
          duration: 60,
          offset_seconds: -1.96
        },
        {
          duration: 30,
          offset_seconds: -0.64
        }
      ]
    )

    expect(normalizer)
      .to have_received(:call)
      .with(
        raw_srt,
        offset: 118.04,
        input_start_at: 0,
        input_end_at: 60,
        start_at: 120,
        end_at: 180
      )
      .ordered

    expect(normalizer)
      .to have_received(:call)
      .with(
        raw_srt,
        offset: 119.36,
        input_start_at: 60,
        input_end_at: 90,
        start_at: 180,
        end_at: 210
      )
      .ordered

    expect(result).to eq(
      "composed subtitles\n"
    )
  end
end
