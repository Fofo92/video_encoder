# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI do
  it 'routes enqueue-trim-export to its command' do
    repo = instance_double(
      VideoEncoder::Persistence::JobRepository
    )
    command = instance_double(
      VideoEncoder::CLI::EnqueueTrimExportCommand
    )

    cli = described_class.new(
      [
        'enqueue-trim-export',
        'movie.json',
        '--output',
        'movie.mkv'
      ],
      config: {}
    )

    allow(cli).to receive(:repo)
      .and_return(repo)

    allow(
      VideoEncoder::CLI::EnqueueTrimExportCommand
    ).to receive(:new)
      .with(
        argv: [
          'movie.json',
          '--output',
          'movie.mkv'
        ],
        repo: repo
      )
      .and_return(command)

    allow(command).to receive(:run)

    expect { cli.run }.not_to raise_error

    expect(command).to have_received(:run).once
  end
end
