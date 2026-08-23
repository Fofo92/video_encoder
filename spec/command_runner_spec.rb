# frozen_string_literal: true

require 'spec_helper'

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
    it 'logs and executes command arguments without a shell' do
      allow(logger).to receive(:info)
      allow(executor).to receive(:system)

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
        exception: true
      )
    end
  end
end
