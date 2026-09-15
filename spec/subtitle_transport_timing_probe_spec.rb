# frozen_string_literal: true

require 'spec_helper'
require 'open3'

RSpec.describe VideoEncoder::SubtitleTransportTimingProbe do
  it 'reads the first subtitle timestamp' do
    status = instance_double(
      Process::Status,
      success?: true
    )

    output = JSON.generate(
      'streams' => [
        {
          'start_time' => '1.240000'
        }
      ]
    )

    executor = class_double(Open3)

    allow(executor)
      .to receive(:capture3)
      .and_return([output, '', status])

    probe = described_class.new(
      executor: executor
    )

    result = probe.call(
      '/tmp/subtitle_segment.ts'
    )

    expect(result).to eq(1.24)

    expect(executor)
      .to have_received(:capture3)
      .with(
        'ffprobe',
        '-v', 'error',
        '-select_streams', 's:0',
        '-show_entries', 'stream=start_time',
        '-of', 'json',
        '/tmp/subtitle_segment.ts'
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

    probe = described_class.new(
      executor: executor
    )

    expect do
      probe.call('/tmp/subtitle_segment.ts')
    end.to raise_error(
      described_class::TimestampUnavailable,
      'subtitle timestamp is unavailable'
    )
  end

  it 'preserves an ffprobe failure diagnostic' do
    status = instance_double(
      Process::Status,
      success?: false,
      exitstatus: 1,
      termsig: nil,
      to_s: 'exit 1'
    )

    executor = class_double(Open3)

    allow(executor)
      .to receive(:capture3)
      .and_return(
        [
          '',
          "invalid transport\n",
          status
        ]
      )

    probe = described_class.new(
      executor: executor
    )

    expect do
      probe.call('/tmp/subtitle_segment.ts')
    end.to raise_error(
      VideoEncoder::CommandRunner::CommandFailed,
      /invalid transport/
    )
  end
end
