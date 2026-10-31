# frozen_string_literal: true

require 'tmpdir'
require 'sequel'
require 'spec_helper'
require_relative '../lib/video_encoder/quarantine_policy'
require_relative '../lib/video_encoder/quarantine_source'

RSpec.describe VideoEncoder::QuarantinePolicy do # rubocop:disable Metrics/BlockLength
  around do |example|
    Dir.mktmpdir do |root|
      @root = root
      @quarantine = File.join(root, 'Quarantaine')
      Dir.mkdir(@quarantine)
      @original = File.join(root, 'capture.m2t')
      @path = File.join(@quarantine, 'capture.m2t')
      File.write(@original, 'capture data')
      @project = File.join(root, 'Film.json')
      @output = File.join(root, 'Film.mkv')
      @db = Sequel.sqlite(File.join(root, 'queue.sqlite3'))
      @db.create_table(:jobs) do
        primary_key :id
        String :project_path
        String :output_path
        String :status
      end
      @now = Time.utc(2026, 10, 31, 12)
      @clock = -> { @now }
      @ledger = VideoEncoder::QuarantineLedger.new(database: @db, root: @quarantine, clock: @clock)
      @policy = described_class.new(database: @db, root: @quarantine, clock: @clock)
      project(@project, @output)
      example.run
    ensure
      @db&.disconnect
    end
  end

  def project(path, output, status: 'done', sources: [@original])
    File.write(path, JSON.generate(format: 'video_encoder.trim_project', version: 2,
                                   sources: sources.map { |source| { path: source } }, timeline: []))
    File.write(output, 'encoded film')
    @db[:jobs].insert(project_path: path, output_path: output, status: status)
  end

  def move
    check = instance_double(VideoEncoder::SourceQuarantineCheck)
    result = VideoEncoder::SourceQuarantineCheck::Result.new(source: Pathname(@original), reasons: [], active_jobs: [])
    allow(check).to receive(:call).and_return(result)
    VideoEncoder::QuarantineSource.new(check: check, quarantine_directory: @quarantine,
                                       journal: @ledger).call(@original)
  end

  def entry
    @policy.list[:entries].first
  end

  def expire
    @now += 30 * 24 * 60 * 60
  end

  def receipt(project = @project, output = @output)
    data = { format: 'video_encoder.completed_export', version: 1, project_path: project, output_path: output,
             project_sha256: Digest::SHA256.file(project).hexdigest, byte_size: File.size(output),
             modified_at: File.mtime(output).utc.iso8601(6) }
    File.write("#{output}.video_encoder-export.json", JSON.generate(data))
  end

  it 'records the real move date and schedules thirty full days later' do
    move
    expect(entry[:state]).to eq('scheduled')
    expect(Time.iso8601(entry[:entered_at])).to eq(@now)
    expect(Time.iso8601(entry[:delete_after]) - @now).to eq(30 * 24 * 60 * 60)
    expect(File.exist?(@original)).to be(false)
    expect(File.read(@path)).to eq('capture data')
  end

  it 'keeps preview read-only even for an expired eligible capture' do
    move
    expire
    before = @db[:quarantine_sources].all
    expect(@policy.sweep[:entries].first[:state]).to eq('due')
    expect(File.exist?(@path)).to be(true)
    expect(@db[:quarantine_sources].all).to eq(before)
  end

  it 'does not remove a capture one second before its deadline' do
    move
    expire
    @now -= 1
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(File.exist?(@path)).to be(true)
  end

  it 'deletes at the deadline without a manual confirmation and preserves projects outputs and history' do
    move
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to eq([@path])
    expect(File.exist?(@path)).to be(false)
    expect(File.exist?(@project)).to be(true)
    expect(File.exist?(@output)).to be(true)
    expect(@db[:jobs].count).to eq(1)
    expect(@db[:quarantine_sources].first[:deleted_at]).not_to be_nil
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
  end

  it 'retains a capture when any output from a shared source is missing' do
    other_project = File.join(@root, 'Episode2.json')
    other_output = File.join(@root, 'Episode2.mkv')
    project(other_project, other_output)
    move
    File.unlink(other_output)
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(entry[:state]).to eq('blocked')
  end

  it 'does not require the missing output of a failed attempt superseded by a completed job for the same project' do
    old_output = File.join(@root, 'failed-output.mkv')
    @db[:jobs].insert(project_path: @project, output_path: old_output, status: 'failed')
    move
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to eq([@path])
  end

  it 'remembers a required project even after its job disappears' do
    move
    @db[:jobs].delete
    File.unlink(@project)
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(entry[:reason]).to include(@project)
  end

  it 'checks new projects added after quarantine entry' do
    move
    project(File.join(@root, 'later.json'), File.join(@root, 'later.mkv'), status: 'queued')
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(entry[:reason]).to include('tâche active')
  end

  %w[running queued deferred].each do |status|
    it "protects a source referenced by a #{status} job at its quarantine path" do
      move
      project(File.join(@root, 'active.json'), File.join(@root, 'active.mkv'), status: status, sources: [@path])
      expire
      expect(@policy.sweep(apply: true)[:deleted]).to be_empty
      expect(File.exist?(@path)).to be(true)
    end
  end

  it 'protects a source used via another hard link' do
    move
    alias_path = File.join(@root, 'alias.m2t')
    File.link(@path, alias_path)
    project(File.join(@root, 'alias.json'), File.join(@root, 'alias.mkv'), status: 'running', sources: [alias_path])
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
  end

  it 'blocks globally when an active project cannot be inspected' do
    move
    @db[:jobs].insert(project_path: File.join(@root, 'missing.json'), output_path: @output, status: 'running')
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(entry[:reason]).to include('actif invérifiable')
  end

  it 'retains a modified project rather than accepting a stale done job' do
    move
    File.write(@project, "#{File.read(@project)}\n")
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(entry[:reason]).to include('modifié')
  end

  it 'retains a changed encoded output' do
    move
    File.write(@output, 'replacement result')
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
  end

  it 'retains a replaced or modified capture' do
    move
    File.write(@path, 'replacement capture')
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(entry[:reason]).to include('modifiée')
  end

  it 'does not follow a symbolic link replacing the capture' do
    move
    File.unlink(@path)
    File.symlink(@output, @path)
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(File.read(@output)).to eq('encoded film')
  end

  it 'blocks if the source reappears at its original location' do
    move
    File.write(@original, 'new capture')
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
  end

  it 'blocks an export workspace even when the old output is complete' do
    move
    Dir.mkdir(VideoEncoder::TrimWorkspace.directory_for(@output))
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(entry[:reason]).to include('travail')
  end

  it 'validates an exact completion receipt including subsecond timestamps' do
    receipt
    move
    @db[:jobs].delete
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to eq([@path])
  end

  it 'does not fall back to a done job if an existing receipt is invalid' do
    receipt
    File.write("#{@output}.video_encoder-export.json", '{}')
    move
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
  end

  it 'never assigns a date or deletes an unverified legacy file during maintenance' do
    File.rename(@original, @path)
    File.unlink(@output)
    @now += 365 * 24 * 60 * 60
    expect(entry[:state]).to eq('untracked')
    expect(entry[:delete_after]).to be_nil
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(@db[:quarantine_sources].count).to eq(0)
  end

  it 'automatically starts a fresh thirty-day period for verified legacy captures without deleting them' do
    File.rename(@original, @path)
    File.utime(Time.utc(2000), Time.utc(2000), @path)
    expect(@policy.sweep(apply: true)[:deleted]).to be_empty
    expect(Time.iso8601(entry[:entered_at])).to eq(@now)
    expect(entry[:state]).to eq('scheduled')
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to eq([@path])
  end

  it 'starts the legacy delay today only after checking project and output evidence' do
    File.rename(@original, @path)
    File.utime(Time.utc(2000), Time.utc(2000), @path)
    @policy.enroll(@path)
    expect(Time.iso8601(entry[:entered_at])).to eq(@now)
    expect(entry[:state]).to eq('scheduled')
    expect { @policy.enroll(@path) }.to raise_error(VideoEncoder::QuarantinePolicyError, /déjà suivie/)
  end

  it 'refuses legacy activation without a nonempty completed output' do
    File.rename(@original, @path)
    File.write(@output, '')
    expect { @policy.enroll(@path) }.to raise_error(VideoEncoder::QuarantinePolicyError)
    expect(entry[:state]).to eq('untracked')
  end

  it 'refuses ambiguous original paths for a legacy filename' do
    File.rename(@original, @path)
    project(File.join(@root, 'other.json'), File.join(@root, 'other.mkv'),
            sources: [File.join(@root, 'elsewhere/capture.m2t')])
    expect { @policy.enroll(@path) }.to raise_error(VideoEncoder::QuarantinePolicyError, /ambiguë/)
  end

  it 'allows explicit project association when only its completion receipt remains' do
    File.rename(@original, @path)
    receipt
    @db[:jobs].delete
    @policy.enroll(@path, project: @project)
    expect(entry[:state]).to eq('scheduled')
    expire
    expect(@policy.sweep(apply: true)[:deleted]).to eq([@path])
  end

  it 'never allows enrollment of a path outside the configured quarantine' do
    expect { @policy.enroll(@original) }.to raise_error(VideoEncoder::QuarantinePolicyError)
    expect(File.exist?(@original)).to be(true)
  end

  it 'holds the queue writer lock through the actual unlink' do
    move
    expire
    other = Sequel.sqlite(File.join(@root, 'queue.sqlite3'), timeout: 0)
    allow(File).to receive(:unlink).and_call_original
    expect(File).to receive(:unlink).with(@path).and_wrap_original do |operation, path|
      expect do
        other[:jobs].insert(project_path: @project, output_path: @output, status: 'queued')
      end.to raise_error(Sequel::DatabaseError, /locked/)
      operation.call(path)
    end
    expect(@policy.sweep(apply: true)[:deleted]).to eq([@path])
  ensure
    other&.disconnect
  end

  it 'rolls back the destination link and preserves the source if recording fails' do
    allow(@ledger).to receive(:record).and_raise(VideoEncoder::QuarantinePolicyError, 'disk full')
    expect { move }.to raise_error(VideoEncoder::QuarantineSource::Error, /source conservée/)
    expect(File.exist?(@original)).to be(true)
    expect(File.exist?(@path)).to be(false)
  end
end
