# frozen_string_literal: true

require 'json'
require 'open3'
require 'spec_helper'

RSpec.describe 'bin/video_encoder_import_trim_session' do
  let(:executable) do
    File.expand_path(
      '../bin/video_encoder_import_trim_session',
      __dir__
    )
  end

  it 'writes the persistent project to standard output' do
    input = JSON.generate(
      format: 'video_encoder.trim_session',
      version: 1,
      sources: [],
      timeline: []
    )

    stdout, stderr, status = Open3.capture3(
      executable,
      stdin_data: input
    )

    expect(status).to be_success
    expect(stderr).to be_empty

    expect(JSON.parse(stdout)).to eq(
      'format' => 'video_encoder.trim_project',
      'version' => 2,
      'sources' => [],
      'timeline' => []
    )
  end

  it 'reports invalid input as JSON without a backtrace' do
    stdout, stderr, status = Open3.capture3(
      executable,
      stdin_data: 'JSON invalide'
    )

    expect(status.exitstatus).to eq(1)
    expect(stdout).to be_empty

    expect(JSON.parse(stderr)).to match(
      'error' => {
        'type' => 'JSON::ParserError',
        'message' => a_string_matching(/unexpected character/)
      }
    )
  end
end
