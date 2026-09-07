# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI do
  it 'routes source-usage with the source path' do
    repo = instance_double(
      VideoEncoder::Persistence::JobRepository
    )

    command = instance_double(
      VideoEncoder::CLI::SourceUsageCommand
    )

    cli = described_class.new(
      [
        'source-usage',
        '/commun/to_be_cut/movie.m2t'
      ],
      config: {}
    )
    allow(cli).to receive(:repo)
      .and_return(repo)

    allow(
      VideoEncoder::CLI::SourceUsageCommand
    ).to receive(:build)
      .with(
        argv: ['/commun/to_be_cut/movie.m2t'],
        repo: repo
      )
      .and_return(command)

    allow(command).to receive(:run)

    expect { cli.run }.not_to raise_error
    expect(command).to have_received(:run).once
  end
end
