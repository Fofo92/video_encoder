# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI do
  it 'routes quarantine-source with explicit confirmation' do
    repo = instance_double(
      VideoEncoder::Persistence::JobRepository
    )
    directories = instance_double(
      VideoEncoder::Directories,
      quarantine: '/commun/Quarantaine'
    )
    config = instance_double(
      VideoEncoder::Config,
      directories: directories
    )
    command = instance_double(
      VideoEncoder::CLI::QuarantineSourceCommand
    )

    cli = described_class.new(
      [
        'quarantine-source',
        '/commun/to_be_cut/movie.m2t',
        '--confirm'
      ],
      config: config
    )

    allow(cli).to receive(:repo)
      .and_return(repo)

    allow(
      VideoEncoder::CLI::QuarantineSourceCommand
    ).to receive(:build)
      .with(
        argv: [
          '/commun/to_be_cut/movie.m2t',
          '--confirm'
        ],
        repo: repo,
        config: config
      )
      .and_return(command)

    allow(command).to receive(:run)

    expect { cli.run }.not_to raise_error
    expect(command).to have_received(:run).once
  end
end
