# frozen_string_literal: true

require 'spec_helper'
require 'open3'

RSpec.describe VideoEncoder::SubtitleTransportTimingProbe do
  it 'reads the subtitle clock origin' do
    status = instance_double(
      Process::Status,
      success?: true
    )

    executor = class_double(Open3)

    allow(executor)
      .to receive(:capture3)
      .and_return(
        [
          JSON.generate(
            'streams' => [
              {
                'start_time' => '3.060000'
              }
            ]
          ),
          '',
          status
        ]
      )

    result = described_class.new(
      executor: executor
    ).call('/tmp/subtitle_project_0.ts')

    expect(result).to eq(3.06)

    expect(executor)
      .to have_received(:capture3)
      .with(
        'ffprobe',
        '-v', 'error',
        '-select_streams', 's:0',
        '-show_entries', 'stream=start_time',
        '-of', 'json',
        '/tmp/subtitle_project_0.ts'
      )
  end

  it 'reports an unavailable subtitle timestamp' do
    status = instance_double(
      Process::Status,
      success?: true
    )

    executor = class_double(Open3)

    allow(executor)
      .to receive(:capture3)
      .and_return(
        [
          JSON.generate('streams' => []),
          '',
          status
        ]
      )

    expect do
      described_class.new(
        executor: executor
      ).call('/tmp/subtitle_project_0.ts')
    end.to raise_error(
      described_class::TimestampUnavailable,
      'subtitle timestamp is unavailable'
    )
  end
end
