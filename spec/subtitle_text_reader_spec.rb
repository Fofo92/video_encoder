# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SubtitleTextReader do
  subject(:text_reader) do
    described_class.new(reader: binary_reader)
  end

  let(:binary_reader) { class_double(File) }

  it 'preserves valid UTF-8 subtitle text' do
    subtitle = "Les petites sœurs de Sainte-Monica\n"

    allow(binary_reader)
      .to receive(:binread)
      .with('/tmp/subtitles.srt')
      .and_return(subtitle.b)

    result = text_reader.read('/tmp/subtitles.srt')

    expect(result).to eq(subtitle)
    expect(result.encoding).to eq(Encoding::UTF_8)
    expect(result).to be_valid_encoding
  end

  it 'drops only invalid bytes produced by subtitle OCR' do
    invalid_bytes = [0xE2, 0x80].pack('C*')
    subtitle = (
      'avant '.b +
      invalid_bytes +
      "* après\n".b
    )

    allow(binary_reader)
      .to receive(:binread)
      .with('/tmp/subtitles.srt')
      .and_return(subtitle)

    result = text_reader.read('/tmp/subtitles.srt')

    expect(result).to eq("avant * après\n")
    expect(result.encoding).to eq(Encoding::UTF_8)
    expect(result).to be_valid_encoding
  end
end
