# frozen_string_literal: true

require 'open3'

RSpec.describe 'VideoEncoder CLI' do
  it 'prints version' do
    stdout, _stderr, status = Open3.capture3('bin/video_encoder version')

    expect(status.success?).to eq(true)
    expect(stdout.strip).to eq(VideoEncoder::VERSION)
  end

  it 'shows usage for unknown command' do
    stdout, _stderr, status = Open3.capture3('bin/video_encoder unknown')

    expect(status.success?).to eq(false)
    expect(stdout).to include('Usage')
  end
end
