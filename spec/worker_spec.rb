# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Worker do
  let(:repo)    { instance_double(VideoEncoder::Persistence::JobRepository) }
  let(:encoder) { instance_double(VideoEncoder::Encoder::Base) }
  let(:logger)  { instance_double(Logger, info: nil) }

  let(:verifier) { instance_double(VideoEncoder::Verifier) }
  let(:job) { VideoEncoder::Job.new(source: 'video.mp4') }
  let(:workspace) { instance_double(VideoEncoder::Workspace) }

  subject(:worker) do
    described_class.new(
      repo: repo,
      encoder: encoder,
      verifier: verifier,
      logger: logger,
      workspace: workspace
      )
    end


  describe '#run_once' do
    before do
      allow(repo).to receive(:next).and_return(job, nil)
      allow(repo).to receive(:mark_running)
      allow(repo).to receive(:mark_done)

      allow(encoder).to receive(:encode).and_return('encoded/video.mkv')

      allow(verifier).to receive(:verify!)
        .with('encoded/video.mkv')
        .and_return(true)

      allow(FileUtils).to receive(:mv)

      allow(workspace)
        .to receive(:move_to_encoding)
        .and_return("/commun/Encoding/video.mp4")

      allow(workspace)
        .to receive(:finalize)
        .and_return("/commun/Encoded/video.mkv")

      allow(workspace)
        .to receive(:remove_partial_output)
    end

    it 'processes a queued job' do
      worker.run_once

      expect(repo).to have_received(:mark_running).with(job)
      expect(encoder)
        .to have_received(:encode) do |encoding_job|
          expect(encoding_job.source.to_s)
            .to eq('/commun/Encoding/video.mp4')
        end

      expect(repo).to have_received(:mark_done) do |done_job|
        expect(done_job.source.to_s)
          .to eq('/commun/Encoding/video.mp4')
      end
      expect(verifier)
        .to have_received(:verify!)
        .with('encoded/video.mkv')
      expect(repo).to have_received(:mark_done) do |done_job|
        expect(done_job.source.to_s)
          .to eq('/commun/Encoding/video.mp4')
      end
    end
  end

  context 'when the encoder fails' do
    before do
      allow(repo).to receive(:next).and_return(job, nil)
      allow(repo).to receive(:mark_running)
      allow(repo).to receive(:mark_failed)
      allow(workspace)
        .to receive(:move_to_encoding)
        .and_return('/commun/Encoding/video.mp4')

      allow(encoder).to receive(:encode)
        .and_raise(StandardError, 'boom')
    end

    it 'marks the job as failed' do
      worker.run_once

      expect(repo).to have_received(:mark_running).with(job)

      expect(repo).to have_received(:mark_failed) do |failed_job, message|
        # p failed_job
        # p failed_job.source
        # p message
        expect(failed_job.source.to_s)
          .to eq('/commun/Encoding/video.mp4')

        expect(message).to eq('boom')
      end
    end
  end

  context 'when there are no queued jobs' do
    before do
      allow(repo).to receive(:next).and_return(nil)
      allow(repo).to receive(:mark_running)
      allow(repo).to receive(:mark_done)
      allow(repo).to receive(:mark_failed)
      allow(encoder).to receive(:encode)
      allow(FileUtils).to receive(:mv)
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
