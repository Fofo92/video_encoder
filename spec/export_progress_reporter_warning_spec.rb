# frozen_string_literal: true

require 'spec_helper'
require 'stringio'

RSpec.describe VideoEncoder::ExportProgressReporter, '#warning' do
  it 'writes a structured warning and flushes the output' do
    output = StringIO.new
    reporter = described_class.new(output: output)

    allow(output).to receive(:flush).and_call_original

    reporter.warning(
      code: 'no_subtitles_found',
      message: 'Aucun sous-titre trouvé pour ce groupe.',
      group: 1
    )

    line = output.string
    prefix = described_class::PREFIX

    expect(line).to start_with(prefix)

    event = JSON.parse(line.delete_prefix(prefix))

    expect(event).to eq(
      'type' => 'warning',
      'code' => 'no_subtitles_found',
      'message' => 'Aucun sous-titre trouvé pour ce groupe.',
      'group' => 1
    )

    expect(output).to have_received(:flush)
  end
end
