# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'
require 'fileutils'

RSpec.describe VideoEncoder::Cleaner do
  let(:logger) { instance_double(Logger, info: nil) }

  subject(:cleaner) do
    described_class.new(logger: logger)
  end

  around do |example|
    Dir.mktmpdir do |dir|
      @dir = dir
      example.run
    end
  end

  it 'removes the source file' do
    source = File.join(@dir, 'video.mkv')
    File.write(source, 'dummy')

    cleaner.clean(source)

    expect(File).not_to exist(source)
  end

  it 'does nothing when the file does not exist' do
    expect {
      cleaner.clean(File.join(@dir, 'missing.mkv'))
    }.not_to raise_error
  end
end
