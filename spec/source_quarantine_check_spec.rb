# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::SourceQuarantineCheck do
  subject(:check) do
    described_class.new(
      source_usage: source_usage,
      file: file
    )
  end

  let(:source_usage) do
    instance_double(
      VideoEncoder::ActiveTrimExportSourceUsage
    )
  end

  let(:file) { class_double(File) }
  let(:source) { '/commun/to_be_cut/movie.m2t' }

  it 'accepts an existing unused source' do
    allow(file).to receive(:file?)
      .with(source)
      .and_return(true)

    allow(source_usage).to receive(:call)
      .with(source)
      .and_return([])

    result = check.call(source)

    expect(result).to be_eligible
    expect(result.reasons).to be_empty
    expect(result.active_jobs).to be_empty
  end

  it 'protects a source used by active exports' do
    job = instance_double(
      VideoEncoder::TrimExportJob
    )

    allow(file).to receive(:file?)
      .with(source)
      .and_return(true)

    allow(source_usage).to receive(:call)
      .with(source)
      .and_return([job])

    result = check.call(source)

    expect(result).not_to be_eligible
    expect(result.reasons).to eq(
      [:active_trim_exports]
    )
    expect(result.active_jobs).to eq([job])
  end

  it 'rejects a missing source' do
    allow(file).to receive(:file?)
      .with(source)
      .and_return(false)
    expect(source_usage).not_to receive(:call)
    result = check.call(source)

    expect(result).not_to be_eligible
    expect(result.reasons).to eq(
      [:source_missing]
    )
  end
end
