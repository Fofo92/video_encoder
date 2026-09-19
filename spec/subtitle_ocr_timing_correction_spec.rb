# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleOcrTimingCorrection do
  let(:timing_probe) do
    instance_double(
      VideoEncoder::SubtitleTransportTimingProbe
    )
  end

  subject(:correction) do
    described_class.new(
      timing_probe: timing_probe,
      tolerance_seconds: 0.08
    )
  end

  it 'restores a transport origin missing from the OCR timestamps' do
    srt = <<~SRT
      1
      00:00:00,920 --> 00:00:02,039
      Salut, Los Angeles !

    SRT

    allow(timing_probe)
      .to receive(:call)
      .with('/tmp/subtitle_project.ts')
      .and_return(3.06)

    result = correction.call(
      srt: srt,
      transport_path: '/tmp/subtitle_project.ts',
      alignment_offset: -0.48
    )

    expect(result).to eq(2.58)
  end

  it 'keeps the alignment correction when OCR includes the origin' do
    srt = <<~SRT
      1
      00:00:04,020 --> 00:00:05,059
      Maman ?

    SRT

    allow(timing_probe)
      .to receive(:call)
      .with('/tmp/subtitle_project.ts')
      .and_return(4.02)

    result = correction.call(
      srt: srt,
      transport_path: '/tmp/subtitle_project.ts',
      alignment_offset: -0.48
    )

    expect(result).to eq(-0.48)
  end

  it 'tolerates timestamp rounding around the transport origin' do
    srt = <<~SRT
      1
      00:00:04,000 --> 00:00:05,039
      Maman ?

    SRT

    allow(timing_probe)
      .to receive(:call)
      .with('/tmp/subtitle_project.ts')
      .and_return(4.02)

    result = correction.call(
      srt: srt,
      transport_path: '/tmp/subtitle_project.ts',
      alignment_offset: -0.48
    )

    expect(result).to eq(-0.48)
  end

  it 'reports an unavailable OCR timestamp' do
    allow(timing_probe)
      .to receive(:call)
      .with('/tmp/subtitle_project.ts')
      .and_return(3.06)

    expect do
      correction.call(
        srt: "aucun horodatage\n",
        transport_path: '/tmp/subtitle_project.ts',
        alignment_offset: -0.48
      )
    end.to raise_error(
      described_class::TimestampUnavailable,
      'OCR subtitle timestamp is unavailable'
    )
  end
end
