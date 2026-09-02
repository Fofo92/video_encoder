# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI::RunTrimExportsCommand do
  let(:repo) do
    instance_double(
      VideoEncoder::Persistence::JobRepository
    )
  end

  let(:worker) do
    instance_double(
      VideoEncoder::TrimExportWorker
    )
  end

  let(:dependency_checker) do
    instance_double(
      VideoEncoder::ExternalDependencyChecker
    )
  end

  let(:command_probe) do
    instance_double(
      VideoEncoder::ExternalCommandProbe
    )
  end

  before do
    allow(dependency_checker).to receive(:call)
    allow(command_probe).to receive(:call)
    allow(worker).to receive(:run_once)
    allow(worker).to receive(:run)
  end

  it 'processes the queued exports once' do
    command = described_class.new(
      argv: ['--once'],
      repo: repo,
      dependency_checker: dependency_checker,
      command_probe: command_probe,
      worker: worker
    )

    command.run

    expect(worker).to have_received(:run_once).once
    expect(worker).not_to have_received(:run)
  end

  it 'runs continuously by default' do
    command = described_class.new(
      argv: [],
      repo: repo,
      dependency_checker: dependency_checker,
      command_probe: command_probe,
      worker: worker
    )

    command.run

    expect(worker).to have_received(:run).once
    expect(worker).not_to have_received(:run_once)
  end

  it 'rejects unsupported arguments' do
    command = described_class.new(
      argv: ['unexpected'],
      repo: repo,
      dependency_checker: dependency_checker,
      command_probe: command_probe,
      worker: worker
    )

    expect { command.run }
      .to raise_error(
        SystemExit,
        'Usage: video_encoder run-trim-exports ' \
        '[--once]'
      )
  end
end
