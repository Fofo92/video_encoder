# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ExternalCommandProbe do
  subject(:probe) do
    described_class.new(capture: capture)
  end

  let(:capture) { double('command capture') }

  describe '#call' do
    it 'accepts a command whose probe succeeds' do
      status = instance_double(
        Process::Status,
        success?: true
      )

      allow(capture).to receive(:call)
        .with('/usr/bin/ccextractor', '--version')
        .and_return(['CCExtractor 0.96.6', '', status])

      expect do
        probe.call('/usr/bin/ccextractor', '--version')
      end.not_to raise_error
    end

    it 'reports a command whose probe fails' do
      status = instance_double(
        Process::Status,
        success?: false
      )

      allow(capture).to receive(:call)
        .with('/usr/bin/ccextractor', '--version')
        .and_return(
          [
            '',
            'docker: image not found',
            status
          ]
        )

      expect do
        probe.call('/usr/bin/ccextractor', '--version')
      end.to raise_error(
        VideoEncoder::MissingExternalDependenciesError,
        'external dependency unavailable: ' \
        '/usr/bin/ccextractor: docker: image not found'
      )
    end

    it 'reports a command that cannot be started' do
      allow(capture).to receive(:call)
        .with('/missing/ccextractor', '--version')
        .and_raise(Errno::ENOENT)

      expect do
        probe.call('/missing/ccextractor', '--version')
      end.to raise_error(
        VideoEncoder::MissingExternalDependenciesError,
        'external dependency unavailable: /missing/ccextractor'
      )
    end
  end
end
