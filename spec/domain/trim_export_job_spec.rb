# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimExportJob do
  subject(:job) do
    described_class.new(
      project_path: 'movie.json',
      output_path: 'movie.mkv'
    )
  end

  describe '#initialization' do
    it 'identifies a trim export job' do
      expect(job.kind).to eq('trim_export')
    end

    it 'generates an id' do
      expect(job.id).not_to be_nil
    end

    it 'stores its paths as pathnames' do
      expect(job.project_path).to be_a(Pathname)
      expect(job.output_path).to be_a(Pathname)
    end

    it 'is queued with no attempt by default' do
      expect(job).to be_queued
      expect(job.attempts).to eq(0)
    end

    it 'exposes its project as the input path' do
      expect(job.input_path).to eq(
        Pathname('movie.json')
      )
      expect(job.output_path).to eq(
        Pathname('movie.mkv')
      )
    end
  end
end
