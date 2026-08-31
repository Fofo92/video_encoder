# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI do
  it 'routes preflight-audio to its command with the project path' do
    dependency_checker = instance_double(
      VideoEncoder::ExternalDependencyChecker
    )
    command = instance_double(
      VideoEncoder::CLI::PreflightAudioCommand
    )

    allow(VideoEncoder::CLI::PreflightAudioCommand).to receive(:new)
      .with(
        argv: ['/projects/movie.json'],
        dependency_checker: dependency_checker
      )
      .and_return(command)
    allow(command).to receive(:run)

    cli = described_class.new(
      ['preflight-audio', '/projects/movie.json'],
      config: {},
      dependency_checker: dependency_checker
    )

    expect { cli.run }.not_to raise_error
    expect(command).to have_received(:run).once
  end
end
