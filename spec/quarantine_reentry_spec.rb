# frozen_string_literal: true

require 'tmpdir'
require 'sequel'
require_relative '../lib/video_encoder/quarantine_ledger'
require_relative '../lib/video_encoder/quarantine_source'
require_relative '../lib/video_encoder/source_quarantine_check'

RSpec.describe VideoEncoder::QuarantineLedger, 'source reentry' do
  around do |example|
    Dir.mktmpdir do |directory|
      @root = File.join(directory, 'quarantine')
      Dir.mkdir(@root)
      @source = File.join(directory, 'Boston.m2t')
      @destination = File.join(@root, 'Boston.m2t')
      File.write(@source, 'capture')
      @database = Sequel.sqlite
      @database.create_table(:jobs) do
        primary_key :id
        String :project_path
        String :output_path
        String :status
      end
      @now = Time.utc(2026, 11, 9)
      @ledger = described_class.new(database: @database, root: @root, clock: -> { @now })
      check = VideoEncoder::SourceQuarantineCheck.new(source_usage: ->(_path) { [] })
      @move = VideoEncoder::QuarantineSource.new(check: check, quarantine_directory: @root, journal: @ledger)
      @move.call(@source)
      @previous = @ledger.current(@destination)
      example.run
    ensure
      @database&.disconnect
    end
  end

  def restore_source
    File.rename(@destination, @source)
    @now += 5 * 24 * 60 * 60
  end

  it 'allows a restored capture to reenter through the normal mover with a fresh thirty day delay' do
    restore_source
    @move.call(@source)
    fresh = @ledger.current(@destination)
    expect(fresh[:entered_at]).to eq(@now.iso8601(6))
    expect(fresh[:delete_after]).to eq((@now + described_class::RETENTION).iso8601(6))
    expect(File.exist?(@source)).to be(false)
    expect(File.read(@destination)).to eq('capture')
    expect(@ledger.entries.size).to eq(1)
    archived = JSON.parse(@database[:quarantine_source_history].first[:entry])
    expect(archived).to eq(JSON.parse(JSON.generate(@previous)))
  end

  it 'does not reset retention for a capture that is already in quarantine' do
    expect { @ledger.record(@source, @destination) }
      .to raise_error(VideoEncoder::QuarantinePolicyError, /déjà suivie/)
    expect(@ledger.current(@destination)).to eq(@previous)
  end

  it 'rejects a destination that is not the same physical file as the restored source' do
    restore_source
    File.write(@destination, 'another capture')
    expect { @ledger.record(@source, @destination) }
      .to raise_error(VideoEncoder::QuarantinePolicyError, /déjà suivie/)
    expect(@ledger.current(@destination)).to eq(@previous)
    expect(File.read(@source)).to eq('capture')
  end

  it 'rolls back the registration and keeps the restored source if the database update fails' do
    restore_source
    @database.run('CREATE TRIGGER reject_reentry BEFORE UPDATE ON quarantine_sources ' \
                  "BEGIN SELECT RAISE(ABORT, 'database failure'); END")
    expect { @move.call(@source) }.to raise_error(VideoEncoder::QuarantineSource::Error, /database failure/)
    expect(@ledger.current(@destination)).to eq(@previous)
    expect(File.read(@source)).to eq('capture')
    expect(File.exist?(@destination)).to be(false)
  end
end
