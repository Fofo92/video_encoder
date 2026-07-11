# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Worker do
  let(:repo)    { instance_double(VideoEncoder::Persistence::JobRepository) }
  let(:encoder) { instance_double(VideoEncoder::Encoder::Base) }
  let(:logger)  { instance_double(Logger, info: nil) }
  let(:config)  { instance_double(VideoEncoder::Config) }
  
  subject(:worker) do
    described_class.new(
      repo: repo,
      encoder: encoder,
      logger: logger,
      config: config
      )
    end

  let(:job) { VideoEncoder::Job.new(source: 'video.mp4') }

  describe '#run_once' do
    before do
      allow(repo).to receive(:next).and_return(job, nil)
      allow(repo).to receive(:mark_running)
      allow(repo).to receive(:mark_done)
      allow(encoder).to receive(:encode)
    end

    it 'processes a queued job' do
      worker.run_once

      expect(repo).to have_received(:mark_running).with(job)
      expect(encoder).to have_received(:encode).with(job)
      expect(repo).to have_received(:mark_done).with(job)
    end
  end

  context 'when the encoder fails' do
    before do
      allow(repo).to receive(:next).and_return(job, nil)
      allow(repo).to receive(:mark_running)
      allow(repo).to receive(:mark_failed)

      allow(encoder).to receive(:encode)
        .and_raise(StandardError, 'boom')
    end

    it 'marks the job as failed' do
      worker.run_once

      expect(repo).to have_received(:mark_running).with(job)
      expect(repo).to have_received(:mark_failed).with(job, 'boom')
    end
  end

  context 'when there are no queued jobs' do
    before do
      allow(repo).to receive(:next).and_return(nil)
      allow(repo).to receive(:mark_running)
      allow(repo).to receive(:mark_done)
      allow(repo).to receive(:mark_failed)
      allow(encoder).to receive(:encode)
    end

    it 'does not process any job' do
      worker.run_once

      expect(encoder).not_to have_received(:encode)
      expect(repo).not_to have_received(:mark_running)
      expect(repo).not_to have_received(:mark_done)
      expect(repo).not_to have_received(:mark_failed)
    end
  end
end
