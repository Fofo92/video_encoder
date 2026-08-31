# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CheckTrimProjectAudioFile do
  it 'loads a persisted project and returns its audio check results' do
    project_path = '/projects/movie.json'
    document = '{"format":"test document"}'
    project = instance_double(VideoEncoder::TrimProject)
    results = [{ analysis: { status: :inconclusive } }]

    reader = class_double(File)
    loader = instance_double(VideoEncoder::TrimProjectLoader)
    checker = instance_double(VideoEncoder::CheckTrimProjectAudio)

    allow(reader).to receive(:read)
      .with(project_path)
      .and_return(document)
    allow(loader).to receive(:load)
      .with(document)
      .and_return(project)
    allow(checker).to receive(:call)
      .with(trim_project: project)
      .and_return(results)

    service = described_class.new(
      reader: reader,
      loader: loader,
      checker: checker
    )

    expect(service.call(project_path: project_path)).to eq(results)
    expect(checker).to have_received(:call)
      .with(trim_project: project).once
  end
end
