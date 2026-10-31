# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'
require 'stringio'

RSpec.describe VideoEncoder::CLI::QuarantineCommand do
  around do |example|
    Dir.mktmpdir do |root|
      @root = root
      @quarantine = File.join(root, 'Quarantaine')
      Dir.mkdir(@quarantine)
      @database_path = File.join(root, 'queue.sqlite3')
      @database = VideoEncoder::Persistence::Database.connect(@database_path)
      @config = VideoEncoder::Config.new('database' => @database_path,
                                         'directories' => { 'quarantine' => @quarantine })
      example.run
    ensure
      @database&.disconnect
    end
  end

  it 'routes list through the real CLI using its configured queue database' do
    expect do
      VideoEncoder::CLI.start(%w[quarantine list], config: @config)
    end.to output(/"format": "video_encoder.quarantine"/).to_stdout
    expect(@database.table_exists?(:quarantine_sources)).to be(true)
  end

  it 'records new quarantine moves through the actual command factory' do
    original = File.join(@root, 'source.m2t')
    File.write(original, 'capture')
    expect do
      VideoEncoder::CLI.start(['quarantine-source', original, '--confirm'], config: @config)
    end.to output(/Source moved to quarantine/).to_stdout
    row = @database[:quarantine_sources].first
    expect(row[:original]).to eq(original)
    expect(File.exist?(row[:path])).to be(true)
    expect(Time.iso8601(row[:delete_after]) - Time.iso8601(row[:entered_at])).to eq(30 * 24 * 60 * 60)
  end

  it 'refuses an unrecognized purge flag instead of deleting anything' do
    output = StringIO.new
    command = described_class.new(argv: %w[sweep --force], database: @database, root: @quarantine, output: output)
    expect { command.run }.to raise_error(SystemExit, /Usage/)
    expect(@database[:quarantine_sources].count).to eq(0)
  end
end
