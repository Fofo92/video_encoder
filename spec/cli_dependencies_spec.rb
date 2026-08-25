# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI do
  let(:worker) { instance_double(VideoEncoder::Worker) }

  before do
    allow(VideoEncoder::Worker)
      .to receive(:new)
      .and_return(worker)

    allow(worker).to receive(:run_once)
    allow(worker).to receive(:run)
  end

  describe '.start' do
    it 'reports missing dependencies without a Ruby backtrace' do
      dependency_checker = instance_double(
        VideoEncoder::ExternalDependencyChecker
      )

      allow(dependency_checker).to receive(:call)
        .with('ffmpeg', 'ffprobe')
        .and_raise(
          VideoEncoder::MissingExternalDependenciesError,
          'missing external dependencies: ffmpeg'
        )

      expect do
        described_class.start(
          ['run', '--once'],
          dependency_checker: dependency_checker
        )
      end.to output(
        "missing external dependencies: ffmpeg\n"
      ).to_stderr.and raise_error(SystemExit)
    end
  end

  describe 'run dependencies' do
    it 'checks the encoding dependencies before running the worker' do
      dependency_checker = instance_double(
        VideoEncoder::ExternalDependencyChecker
      )

      allow(dependency_checker).to receive(:call)

      cli = described_class.new(
        ['run', '--once'],
        dependency_checker: dependency_checker
      )

      cli.run

      expect(dependency_checker).to have_received(:call).with(
        'ffmpeg',
        'ffprobe'
      )
    end

    it 'does not start the worker when a dependency is missing' do
      dependency_checker = instance_double(
        VideoEncoder::ExternalDependencyChecker
      )

      allow(dependency_checker).to receive(:call)
        .with('ffmpeg', 'ffprobe')
        .and_raise(
          VideoEncoder::MissingExternalDependenciesError,
          'missing external dependencies: ffmpeg'
        )

      cli = described_class.new(
        ['run', '--once'],
        dependency_checker: dependency_checker
      )

      expect do
        cli.run
      end.to raise_error(
        VideoEncoder::MissingExternalDependenciesError,
        'missing external dependencies: ffmpeg'
      )

      expect(worker).not_to have_received(:run_once)
      expect(worker).not_to have_received(:run)
    end

    it 'does not check dependencies for the fake encoder' do
      config = VideoEncoder::Config.load
      dependency_checker = instance_double(
        VideoEncoder::ExternalDependencyChecker
      )

      allow(config).to receive(:encoder).and_return('fake')
      allow(dependency_checker).to receive(:call)

      cli = described_class.new(
        ['run', '--once'],
        config: config,
        dependency_checker: dependency_checker
      )

      cli.run

      expect(dependency_checker).not_to have_received(:call)
      expect(worker).to have_received(:run_once)
    end
  end
end
