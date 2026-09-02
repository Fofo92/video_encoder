# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI do
  it 'routes run-trim-exports to its command' do
    repo = instance_double(
      VideoEncoder::Persistence::JobRepository
    )
    dependency_checker = instance_double(
      VideoEncoder::ExternalDependencyChecker
    )
    command_probe = instance_double(
      VideoEncoder::ExternalCommandProbe
    )
    command = instance_double(
      VideoEncoder::CLI::RunTrimExportsCommand
    )

    cli = described_class.new(
      ['run-trim-exports', '--once'],
      config: {},
      dependency_checker: dependency_checker,
      command_probe: command_probe
    )

    allow(cli).to receive(:repo)
      .and_return(repo)

    allow(
      VideoEncoder::CLI::RunTrimExportsCommand
    ).to receive(:new)
      .with(
        argv: ['--once'],
        repo: repo,
        dependency_checker: dependency_checker,
        command_probe: command_probe
      )
      .and_return(command)

    allow(command).to receive(:run)

    expect { cli.run }.not_to raise_error

    expect(command).to have_received(:run).once
  end
end
