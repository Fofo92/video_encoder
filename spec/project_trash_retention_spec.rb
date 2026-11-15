# frozen_string_literal: true

require 'tmpdir'
require 'sequel'
require_relative '../lib/video_encoder/project_removal'
require_relative '../lib/video_encoder/project_trash_retention'

RSpec.describe VideoEncoder::ProjectTrashRetention do
  around do |example|
    Dir.mktmpdir do |root|
      @root = root
      @source = File.join(root, 'capture.m2t')
      @project = File.join(root, 'Film.json')
      @output = File.join(root, 'Film.mkv')
      File.write(@source, 'capture')
      File.write(@project, JSON.generate(format: 'video_encoder.trim_project', version: 2,
                                         sources: [{ path: @source }], timeline: []))
      File.write(@output, 'old video')
      @db = Sequel.sqlite
      @db.create_table(:jobs) do
        primary_key :id
        String :project_path
        String :output_path
        String :status
      end
      @db[:jobs].insert(project_path: @project, output_path: @output, status: 'done')
      removal = VideoEncoder::ProjectRemoval.new(@db)
      plan = removal.call(@project, dependencies: true)
      @directory = removal.call(@project, dependencies: true, token: plan[:token])
      @created = VideoEncoder::ProjectTrashEntry.new(@directory).created_at
      @now = @created + described_class::RETENTION - 1
      @retention = described_class.new(@db, clock: -> { @now })
      example.run
    ensure
      @db&.disconnect
    end
  end

  def expire
    @now = @created + described_class::RETENTION + 1
  end

  it 'keeps entries younger than thirty days and exposes their original creation date' do
    result = @retention.sweep(apply: true)
    expect(result[:entries].first[:state]).to eq('scheduled')
    expect(result[:entries].first[:created_at]).to eq(@created.iso8601(6))
    expect(result[:deleted]).to be_empty
    expect(File.directory?(@directory)).to be(true)
  end

  it 'previews expired entries without deleting files or changing queue history' do
    expire
    before = @db[:jobs].all
    result = @retention.sweep
    expect(result[:entries].first[:state]).to eq('due')
    expect(result[:deleted]).to be_empty
    expect(@db[:jobs].all).to eq(before)
    expect(File.directory?(@directory)).to be(true)
  end

  it 'purges only an expired recovery group while preserving the capture and historical jobs' do
    expire
    before = @db[:jobs].all
    result = @retention.sweep(apply: true)
    expect(result[:deleted]).to eq([@directory])
    expect(result[:entries]).to be_empty
    expect(File.exist?(@directory)).to be(false)
    expect(File.read(@source)).to eq('capture')
    expect(@db[:jobs].all).to eq(before)
  end

  it 'keeps expired files referenced by a queued job' do
    expire
    @db[:jobs].insert(project_path: @project, output_path: @output, status: 'queued')
    result = @retention.sweep(apply: true)
    expect(result[:entries].first[:state]).to eq('blocked')
    expect(result[:deleted]).to be_empty
    expect(File.directory?(@directory)).to be(true)
  end

  it 'rechecks active references under the queue lock after taking the preview' do
    expire
    allow(@retention).to receive(:list).and_wrap_original do |original|
      result = original.call
      @db[:jobs].insert(project_path: @project, output_path: @output, status: 'running')
      result
    end
    result = @retention.sweep(apply: true)
    expect(result[:deleted]).to be_empty
    expect(result[:errors].join).to include('active')
    expect(File.directory?(@directory)).to be(true)
  end

  it 'does not delete an entry whose content changed after the preview' do
    expire
    allow(@retention).to receive(:list).and_wrap_original do |original|
      result = original.call
      manifest = JSON.parse(File.read(File.join(@directory, 'manifest.json')))
      File.write(manifest.fetch(@output), 'changed video')
      result
    end
    result = @retention.sweep(apply: true)
    expect(result[:deleted]).to be_empty
    expect(result[:errors].join).to include('changé')
    expect(File.directory?(@directory)).to be(true)
  end

  it 'falls back to the manifest date when the filesystem has no creation timestamp' do
    allow(File).to receive(:birthtime).with(@directory).and_raise(NotImplementedError)
    older = Time.utc(2026, 1, 1)
    manifest = File.join(@directory, 'manifest.json')
    File.utime(older, older, manifest)
    @now = older + described_class::RETENTION + 1
    result = @retention.sweep
    expect(result[:entries].first[:created_at]).to eq(older.iso8601(6))
    expect(result[:entries].first[:state]).to eq('due')
    expect(File.directory?(@directory)).to be(true)
  end

  it 'does not reset retention when an archived video is modified' do
    manifest = JSON.parse(File.read(File.join(@directory, 'manifest.json')))
    File.write(manifest.fetch(@output), 'changed video')
    expect(VideoEncoder::ProjectTrashEntry.new(@directory).created_at).to eq(@created)
  end

  it 'conserves entries with unexpected content instead of recursively removing them' do
    expire
    File.write(File.join(@directory, 'unexpected'), 'keep')
    result = @retention.sweep(apply: true)
    expect(result[:errors]).not_to be_empty
    expect(result[:deleted]).to be_empty
    expect(File.read(File.join(@directory, 'unexpected'))).to eq('keep')
  end
end
