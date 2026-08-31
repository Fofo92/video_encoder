# frozen_string_literal: true

require 'spec_helper'
require 'json'
require 'stringio'

RSpec.describe VideoEncoder::CLI::PreflightAudioCommand do
  it 'checks dependencies and writes the audio report as JSON' do
    service = instance_double(VideoEncoder::CheckTrimProjectAudioFile)
    dependency_checker = instance_double(
      VideoEncoder::ExternalDependencyChecker
    )
    output = StringIO.new

    allow(dependency_checker).to receive(:call)
      .with('ffmpeg', 'ffprobe')
    allow(service).to receive(:call)
      .with(project_path: '/projects/movie.json')
      .and_return([])

    command = described_class.new(
      argv: ['/projects/movie.json'],
      service: service,
      dependency_checker: dependency_checker,
      output: output
    )

    command.run

    expect(dependency_checker).to have_received(:call)
      .with('ffmpeg', 'ffprobe').once
    expect(service).to have_received(:call)
      .with(project_path: '/projects/movie.json').once
    expect(JSON.parse(output.string)).to eq(
      'version' => 1,
      'audio_checks' => []
    )
  end
end
