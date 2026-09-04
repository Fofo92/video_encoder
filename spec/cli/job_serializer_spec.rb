# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI::JobSerializer do
  subject(:serializer) { described_class.new }

  let(:job) do
    VideoEncoder::TrimExportJob.new(
      id: 'trim-1',
      project_path: '/commun/movie.json',
      output_path: '/videos/movie.mkv',
      status: VideoEncoder::Status::RUNNING,
      attempts: 1,
      created_at: Time.utc(2026, 9, 5, 8, 0, 0),
      started_at: Time.utc(2026, 9, 5, 8, 5, 0)
    )
  end

  it 'serializes a trim export job' do
    expect(serializer.call(job)).to eq(
      id: 'trim-1',
      kind: 'trim_export',
      input_path: '/commun/movie.json',
      output_path: '/videos/movie.mkv',
      status: 'running',
      attempts: 1,
      created_at: '2026-09-05T08:00:00Z',
      started_at: '2026-09-05T08:05:00Z',
      finished_at: nil,
      error: nil
    )
  end
end
