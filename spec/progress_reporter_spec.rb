# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ProgressReporter do
  subject(:reporter) { described_class.new }

  describe '#update' do
    it 'prints a progress bar' do
      expect {
        reporter.update(50)
      }.to output(/\[.*\]\s+50 %/).to_stdout
    end

    it 'caps progress at 100' do
      expect {
        reporter.update(150)
      }.to output(/100 %/).to_stdout
    end

    it 'caps progress at 0' do
      expect {
        reporter.update(-10)
      }.to output(/0 %/).to_stdout
    end
  end

  describe '#finish' do
    it 'prints a newline' do
      expect {
        reporter.finish
      }.to output("\n").to_stdout
    end
  end
end
