# frozen_string_literal: true

require 'spec_helper'
require 'stringio'

RSpec.describe VideoEncoder::CLI::QuarantineSourceCommand do
  let(:quarantine) do
    instance_double(VideoEncoder::QuarantineSource)
  end

  it 'quarantines a confirmed source' do
    output = StringIO.new

    allow(quarantine).to receive(:call)
      .with('/commun/to_be_cut/movie.m2t')
      .and_return(
        Pathname('/commun/Quarantaine/movie.m2t')
      )

    command = described_class.new(
      argv: [
        '/commun/to_be_cut/movie.m2t',
        '--confirm'
      ],
      quarantine: quarantine,
      output: output
    )

    command.run

    expect(output.string).to eq(
      'Source moved to quarantine: ' \
      '/commun/Quarantaine/movie.m2t' \
      "\n"
    )
  end

  it 'requires explicit confirmation' do
    command = described_class.new(
      argv: ['/commun/to_be_cut/movie.m2t'],
      quarantine: quarantine
    )

    expect(quarantine).not_to receive(:call)

    expect { command.run }
      .to raise_error(
        SystemExit,
        'Usage: video_encoder quarantine-source ' \
        '<source> --confirm'
      )
  end

  it 'reports a protected source cleanly' do
    failure = VideoEncoder::QuarantineSource::UnsafeSource.new(
      'source is not eligible: active_trim_exports'
    )

    command = described_class.new(
      argv: [
        '/commun/to_be_cut/movie.m2t',
        '--confirm'
      ],
      quarantine: quarantine
    )

    allow(quarantine).to receive(:call)
      .and_raise(failure)

    expect { command.run }
      .to raise_error(
        SystemExit,
        'source is not eligible: active_trim_exports'
      )
  end
end
