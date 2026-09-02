# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI::JobPresenter do
  subject(:presenter) { described_class.new }

  let(:encoding_job) do
    VideoEncoder::Job.new(
      id: 'encoding-1',
      source: 'video.m2t'
    )
  end

  let(:trim_export_job) do
    VideoEncoder::TrimExportJob.new(
      id: 'trim-1',
      project_path: 'movie.json',
      output_path: 'movie.mkv'
    )
  end

  describe '#summary' do
    it 'formats an encoding job' do
      expect(
        presenter.summary(encoding_job)
      ).to eq(
        'encoding-1 | encoding | ' \
        'video.m2t | - | queued | attempts=0'
      )
    end

    it 'formats a trim export job' do
      expect(
        presenter.summary(trim_export_job)
      ).to eq(
        'trim-1 | trim_export | ' \
        'movie.json | movie.mkv | queued | attempts=0'
      )
    end
  end

  describe '#details' do
    it 'describes a trim export job' do
      expect(
        presenter.details(trim_export_job)
      ).to include(
        'ID:       trim-1',
        'Type:     trim_export',
        'Input:    movie.json',
        'Output:   movie.mkv',
        'Status:   queued',
        'Attempts: 0'
      )
    end
  end

  describe '#failure' do
    it 'includes the failure message' do
      trim_export_job.fail!('boom')

      expect(
        presenter.failure(trim_export_job)
      ).to include(
        'trim-1',
        'movie.json',
        'movie.mkv',
        'error=boom'
      )
    end
  end
end
