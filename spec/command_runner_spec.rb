# frozen_string_literal: true

require 'spec_helper'
require 'rbconfig'
require 'tmpdir'

RSpec.describe VideoEncoder::CommandRunner do
  subject(:runner) do
    described_class.new(
      executor: executor,
      logger: logger
    )
  end

  let(:executor) { instance_double('CommandExecutor') }
  let(:logger) { instance_double('Logger') }

  describe '#run' do
    it 'reports the exit status of a failed command' do
      command_runner = described_class.new

      expect do
        command_runner.run(
          RbConfig.ruby,
          '-e',
          'exit 10'
        )
      end.to raise_error(
        VideoEncoder::CommandRunner::CommandFailed
      ) { |error|
        expect(error.exit_status).to eq(10)
        expect(error.term_signal).to be_nil
      }
    end

    it 'logs and executes command arguments without a shell' do
      allow(logger).to receive(:info)
      allow(executor).to receive(:system).and_return(true)

      runner.run(
        'ffmpeg',
        '-i', '/media/movie.m2t',
        '-c', 'copy',
        '/tmp/movie.mkv'
      )

      expect(logger).to have_received(:info).with(
        'ffmpeg -i /media/movie.m2t -c copy /tmp/movie.mkv'
      )

      expect(executor).to have_received(:system).with(
        'ffmpeg',
        '-i', '/media/movie.m2t',
        '-c', 'copy',
        '/tmp/movie.mkv',
        exception: false
      )
    end
  end

  it 'reports an ordinary command failure' do
    command_runner = described_class.new

    expect do
      command_runner.run(
        RbConfig.ruby,
        '-e',
        'exit 2'
      )
    end.to raise_error(
      VideoEncoder::CommandRunner::CommandFailed
    ) { |error|
      expect(error.exit_status).to eq(2)
      expect(error.term_signal).to be_nil
    }
  end

  it 'reports termination by a signal' do
    command_runner = described_class.new

    expect do
      command_runner.run(
        RbConfig.ruby,
        '-e',
        'Process.kill("TERM", Process.pid)'
      )
    end.to raise_error(
      VideoEncoder::CommandRunner::CommandFailed
    ) { |error|
      expect(error.exit_status).to be_nil
      expect(error.term_signal).to eq(Signal.list.fetch('TERM'))
    }
  end

  it 'does not reuse an earlier exit status when starting fails' do
    command_runner = described_class.new

    expect do
      command_runner.run(
        RbConfig.ruby,
        '-e',
        'exit 10'
      )
    end.to raise_error(
      VideoEncoder::CommandRunner::CommandFailed
    )

    Dir.mktmpdir('video_encoder_command_test') do |directory|
      expect do
        command_runner.run(
          File.join(directory, 'missing_executable')
        )
      end.to raise_error(
        VideoEncoder::CommandRunner::CommandFailed
      ) { |error|
        expect(error.exit_status).to be_nil
        expect(error.term_signal).to be_nil
      }
    end
  end
end
