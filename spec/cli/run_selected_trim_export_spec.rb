# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI::RunTrimExportsCommand, 'selected job' do
  let(:worker) { instance_double(VideoEncoder::TrimExportWorker, run_selected: nil) }
  let(:recovery) { instance_double(VideoEncoder::StaleTrimExportRecovery, call: true) }
  let(:dependencies) { instance_double(VideoEncoder::ExternalDependencyChecker, call: nil) }
  let(:probe) { instance_double(VideoEncoder::ExternalCommandProbe, call: nil) }

  def command(arguments)
    described_class.new(argv: arguments, repo: double('repository'), worker: worker, recovery: recovery,
                        dependency_checker: dependencies, command_probe: probe)
  end

  it 'dispatches exactly the requested id without draining the queue' do
    expect(worker).to receive(:run_selected).with('test-job').once
    expect(worker).not_to receive(:run_once)
    expect(worker).not_to receive(:run)
    command(['--job', 'test-job']).run
  end

  it 'refuses to start the selected job while another worker is active' do
    allow(recovery).to receive(:call).and_return(false)
    expect(worker).not_to receive(:run_selected)
    expect { command(['--job', 'test-job']).run }.to raise_error(SystemExit, /already running/)
  end

  it 'rejects incomplete or combined run modes before inspecting the queue' do
    expect(recovery).not_to receive(:call)
    [['--job'], ['--job', ''], ['--once', '--job', 'test-job']].each do |arguments|
      expect { command(arguments).run }.to raise_error(SystemExit, /Usage:/)
    end
  end
end
