# frozen_string_literal: true

RSpec.describe VideoEncoder::CLI::ManageTrimJobCommand do
  let(:repo) { instance_double(VideoEncoder::Persistence::JobRepository) }

  it 'reports a task without deleting it' do
    expect(repo).to receive(:defer_queued?).with('job').and_return(true)
    command = described_class.new(action: 'defer-job', argv: ['job'], repo: repo)
    expect { command.run }.to output("defer-job: job\n").to_stdout
  end

  it 'changes the destination of the existing task' do
    expect(repo).to receive(:update_pending_output?).with('job', '/new/name.mkv').and_return(true)
    command = described_class.new(action: 'set-job-output', argv: ['job', '--output', '/new/name.mkv'], repo: repo)
    expect { command.run }.to output("set-job-output: job\n").to_stdout
  end

  it 'keeps the project file unless explicitly requested otherwise' do
    expect(repo).to receive(:delete_inactive?).with('job', delete_project: false).and_return(true)
    command = described_class.new(action: 'delete-job', argv: ['job'], repo: repo)
    expect { command.run }.to output("delete-job: job\n").to_stdout
  end

  it 'passes the explicit project deletion option' do
    expect(repo).to receive(:delete_inactive?).with('job', delete_project: true).and_return(true)
    command = described_class.new(action: 'delete-job', argv: ['job', '--delete-project'], repo: repo)
    expect { command.run }.to output("delete-job: job\n").to_stdout
  end

  it 'rejects an invalid delete option before changing any task' do
    expect(repo).not_to receive(:delete_inactive?)
    command = described_class.new(action: 'delete-job', argv: ['job', '--unknown'], repo: repo)
    expect { command.run }.to raise_error(SystemExit)
  end

  it 'reports a validation conflict without a database exception backtrace' do
    allow(repo).to receive(:delete_inactive?).and_raise(
      VideoEncoder::Persistence::JobRepository::QueueActionError, 'the project is referenced by another job'
    )
    command = described_class.new(action: 'delete-job', argv: ['job', '--delete-project'], repo: repo)
    expect do
      expect { command.run }.to raise_error(SystemExit)
    end.to output("the project is referenced by another job\n").to_stderr
  end
end
