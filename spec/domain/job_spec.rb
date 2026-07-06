require 'spec_helper'

RSpec.describe VideoEncoder::Job do
  subject(:job) { described_class.new(source: 'video.mp4') }

  describe '#initialization' do
    it 'generates an id' do
      expect(job.id).not_to be_nil
    end

    it 'stores the source as a Pathname' do
      expect(job.source).to be_a(Pathname)
    end

    it 'has zero attempts' do
      expect(job.attempts).to eq(0)
    end

    it 'is queued by default' do
      expect(job).to be_queued
    end
  end

  describe '#start!' do
    it 'marks the job as running' do
      job.start!

      expect(job).to be_running
      expect(job.started_at).to be_a(Time)
    end
  end

  describe '#finish!' do
    before { job.start! }

    it 'marks the job as done' do
      job.finish!

      expect(job).to be_done
      expect(job.finished_at).to be_a(Time)
    end
  end

  describe '#fail!' do
    it 'marks the job as failed' do
      job.fail!('boom')

      expect(job).to be_failed
      expect(job.error).to eq('boom')
      expect(job.finished_at).to be_a(Time)
    end
  end

end
