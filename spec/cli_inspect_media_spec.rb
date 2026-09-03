# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI do
  it 'routes inspect-media with the source path' do
    dependency_checker = instance_double(
      VideoEncoder::ExternalDependencyChecker
    )
    command = instance_double(
      VideoEncoder::CLI::InspectMediaCommand
    )

    allow(
      VideoEncoder::CLI::InspectMediaCommand
    ).to receive(:new)
      .with(
        argv: ['/commun/movie.m2t'],
        dependency_checker: dependency_checker
      )
      .and_return(command)
    allow(command).to receive(:run)

    cli = described_class.new(
      ['inspect-media', '/commun/movie.m2t'],
      config: {},
      dependency_checker: dependency_checker
    )

    expect { cli.run }.not_to raise_error
    expect(command).to have_received(:run).once
  end
end
