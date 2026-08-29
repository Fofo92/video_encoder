# frozen_string_literal: true

require 'spec_helper'
require 'stringio'

RSpec.describe VideoEncoder::ExportProgressReporter do
  it 'writes a prefixed JSON export event' do
    output = StringIO.new
    reporter = described_class.new(
      output: output
    )

    reporter.call(
      stage: :audio,
      step: 2,
      total: 5,
      track: 1,
      tracks: 2
    )

    line = output.string
    prefix = described_class::PREFIX

    expect(line).to start_with(prefix)

    expect(
      JSON.parse(line.delete_prefix(prefix))
    ).to eq(
      'stage' => 'audio',
      'step' => 2,
      'total' => 5,
      'track' => 1,
      'tracks' => 2
    )
  end
end
