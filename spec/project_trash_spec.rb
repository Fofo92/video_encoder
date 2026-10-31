# frozen_string_literal: true

require 'tmpdir'
require 'sequel'
require_relative '../lib/video_encoder/project_removal'
require_relative '../lib/video_encoder/project_trash'

RSpec.describe VideoEncoder::ProjectTrash do
  around do |example|
    Dir.mktmpdir do |root|
      @root = root
      @project = File.join(root, 'Film.json')
      @output = File.join(root, 'Film.mkv')
      @source = File.join(root, 'capture.m2t')
      @db = Sequel.sqlite
      @db.create_table(:jobs) do
        primary_key :id
        String :project_path
        String :output_path
        String :status
      end
      File.write(@project, JSON.generate(format: 'video_encoder.trim_project', version: 2,
                                         sources: [{ path: @source }], timeline: []))
      File.write(@output, 'movie')
      File.write(@source, 'capture')
      service = VideoEncoder::ProjectRemoval.new(@db)
      preview = service.call(@project, dependencies: true)
      @directory = service.call(@project, dependencies: true, token: preview[:token])
      @trash = described_class.new(@db)
      example.run
    ensure
      @db&.disconnect
    end
  end

  def entry
    @trash.list.fetch(:entries).fetch(0)
  end

  it 'automatically remembers removals and lists grouped size and original paths' do
    expect(@trash.list[:errors]).to be_empty
    expect(entry[:project]).to eq(@project)
    expect(entry[:files]).to contain_exactly(@project, @output)
    expect(entry[:bytes]).to be > 5
    expect(entry[:deleted_at]).to match(/\d{4}-\d\d-\d\dT/)
    expect(described_class.new(@db).list[:entries].size).to eq(1)
  end

  it 'restores a group to original paths and removes its recovery entry' do
    item = entry
    @trash.change('restore', item[:directory], item[:token])
    expect(File.read(@output)).to eq('movie')
    expect(File.read(@project)).to include('video_encoder.trim_project')
    expect(File.read(@source)).to eq('capture')
    expect(@trash.list[:entries]).to be_empty
  end

  it 'never overwrites existing original files' do
    item = entry
    File.write(@output, 'new movie')
    expect do
      @trash.change('restore', item[:directory], item[:token])
    end.to raise_error(VideoEncoder::ProjectTrashError, /présente/)
    expect(File.read(@output)).to eq('new movie')
    expect(File.exist?(@project)).to be(false)
    expect(@trash.list[:entries].size).to eq(1)
  end

  it 'permanently purges only the listed group and preserves captures' do
    item = entry
    @trash.change('purge', item[:directory], item[:token])
    expect(File.exist?(@directory)).to be(false)
    expect(File.read(@source)).to eq('capture')
    expect(@trash.list[:entries]).to be_empty
  end

  it 'rejects a stale listing token without removing files' do
    item = entry
    archived = JSON.parse(File.read(File.join(@directory, 'manifest.json'))).values.last
    File.write(archived, 'modified movie')
    expect do
      @trash.change('purge', item[:directory], item[:token])
    end.to raise_error(VideoEncoder::ProjectTrashError, /changé/)
    expect(File.exist?(archived)).to be(true)
  end

  it 'protects files referred to by active queue jobs' do
    item = entry
    @db[:jobs].insert(project_path: @project, output_path: @output, status: 'queued')
    expect do
      @trash.change('restore', item[:directory], item[:token])
    end.to raise_error(VideoEncoder::ProjectTrashError, /active/)
    expect do
      @trash.change('purge', item[:directory], item[:token])
    end.to raise_error(VideoEncoder::ProjectTrashError, /active/)
  end

  it 'rejects symbolic links and unrecognized extra files' do
    item = entry
    extra = File.join(@directory, 'unexpected')
    File.symlink(@source, extra)
    expect(@trash.list[:errors]).not_to be_empty
    expect { @trash.change('purge', item[:directory], item[:token]) }.to raise_error(VideoEncoder::ProjectTrashError)
    expect(File.read(@source)).to eq('capture')
  end

  it 'reports unavailable roots rather than silently declaring the trash empty' do
    root = File.dirname(@directory)
    File.rename(root, "#{root}-offline")
    expect(@trash.list[:entries]).to be_empty
    expect(@trash.list[:errors].join).to include('indisponible')
  end

  it 'allows manually registering legacy recovery roots without recursively scanning other folders' do
    @db[:project_trash_roots].delete
    expect(@trash.list[:entries]).to be_empty
    @trash.register(File.dirname(@directory))
    expect(@trash.list[:entries].size).to eq(1)
    expect { @trash.register(@root) }.to raise_error(VideoEncoder::ProjectTrashError)
  end

  it 'refuses operations on unregistered paths' do
    item = entry
    @db[:project_trash_roots].delete
    expect do
      @trash.change('purge', item[:directory], item[:token])
    end.to raise_error(VideoEncoder::ProjectTrashError, /enregistrée/)
  end

  it 'protects an archived video used as a capture by another active project' do
    item = entry
    archived = JSON.parse(File.read(File.join(@directory, 'manifest.json'))).fetch(@output)
    other = File.join(@root, 'other.json')
    File.write(other, JSON.generate(format: 'video_encoder.trim_project', version: 2,
                                    sources: [{ path: archived }], timeline: []))
    @db[:jobs].insert(project_path: other, output_path: File.join(@root, 'other.mkv'), status: 'running')
    expect do
      @trash.change('purge', item[:directory], item[:token])
    end.to raise_error(VideoEncoder::ProjectTrashError, /active/)
    expect(File.exist?(archived)).to be(true)
  end

  it 'rolls back exclusive restoration links if a later destination becomes unavailable' do
    item = entry
    archived = JSON.parse(File.read(File.join(@directory, 'manifest.json'))).fetch(@output)
    allow(File).to receive(:link).and_call_original
    allow(File).to receive(:link).with(archived, @output).and_raise(Errno::EEXIST)
    expect { @trash.change('restore', item[:directory], item[:token]) }.to raise_error(Errno::EEXIST)
    expect(File.exist?(@project)).to be(false)
    expect(File.exist?(archived)).to be(true)
    expect(@trash.list[:entries].size).to eq(1)
  end
end
