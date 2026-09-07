# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::QuarantineSource do
  subject(:quarantine) do
    described_class.new(
      check: check,
      quarantine_directory: quarantine_directory,
      file: file
    )
  end

  let(:check) do
    instance_double(
      VideoEncoder::SourceQuarantineCheck
    )
  end

  let(:file) { class_double(File) }

  let(:quarantine_directory) do
    Pathname('/commun/Quarantaine')
  end

  let(:source) do
    Pathname('/commun/to_be_cut/movie.m2t')
  end

  let(:destination) do
    Pathname('/commun/Quarantaine/movie.m2t')
  end

  it 'moves an eligible source without overwriting' do
    result = instance_double(
      VideoEncoder::SourceQuarantineCheck::Result,
      eligible?: true,
      source: source
    )

    allow(check).to receive(:call)
      .with(source)
      .and_return(result)

    allow(file).to receive(:directory?)
      .with(quarantine_directory)
      .and_return(true)

    allow(file).to receive(:exist?)
      .with(destination)
      .and_return(false)

    expect(file).to receive(:link)
      .with(source, destination)
      .ordered

    expect(file).to receive(:unlink)
      .with(source)
      .ordered

    expect(quarantine.call(source))
      .to eq(destination)
  end

  it 'refuses an ineligible source' do
    result = instance_double(
      VideoEncoder::SourceQuarantineCheck::Result,
      eligible?: false,
      reasons: [:active_trim_exports]
    )

    allow(check).to receive(:call)
      .with(source)
      .and_return(result)

    expect(file).not_to receive(:link)
    expect(file).not_to receive(:unlink)

    expect { quarantine.call(source) }
      .to raise_error(
        VideoEncoder::QuarantineSource::UnsafeSource,
        'source is not eligible: active_trim_exports'
      )
  end

  it 'refuses an existing destination' do
    result = instance_double(
      VideoEncoder::SourceQuarantineCheck::Result,
      eligible?: true,
      source: source
    )

    allow(check).to receive(:call)
      .with(source)
      .and_return(result)

    allow(file).to receive(:directory?)
      .with(quarantine_directory)
      .and_return(true)

    allow(file).to receive(:exist?)
      .with(destination)
      .and_return(true)

    expect(file).not_to receive(:link)
    expect(file).not_to receive(:unlink)

    expect { quarantine.call(source) }
      .to raise_error(
        VideoEncoder::QuarantineSource::DestinationExists,
        "quarantine destination already exists: #{destination}"
      )
  end

  it 'refuses a missing quarantine directory' do
    result = instance_double(
      VideoEncoder::SourceQuarantineCheck::Result,
      eligible?: true,
      source: source
    )

    allow(check).to receive(:call)
      .with(source)
      .and_return(result)

    allow(file).to receive(:directory?)
      .with(quarantine_directory)
      .and_return(false)

    expect(file).not_to receive(:link)
    expect(file).not_to receive(:unlink)

    expect { quarantine.call(source) }
      .to raise_error(
        VideoEncoder::QuarantineSource::MissingDirectory,
        "quarantine directory not found: #{quarantine_directory}"
      )
  end

  it 'does not remove the source after a destination race' do
    result = instance_double(
      VideoEncoder::SourceQuarantineCheck::Result,
      eligible?: true,
      source: source
    )

    allow(check).to receive(:call)
      .with(source)
      .and_return(result)

    allow(file).to receive(:directory?)
      .with(quarantine_directory)
      .and_return(true)

    allow(file).to receive(:exist?)
      .with(destination)
      .and_return(false)

    allow(file).to receive(:link)
      .with(source, destination)
      .and_raise(Errno::EEXIST)

    expect(file).not_to receive(:unlink)

    expect { quarantine.call(source) }
      .to raise_error(
        VideoEncoder::QuarantineSource::DestinationExists
      )
  end
end
