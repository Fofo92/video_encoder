# frozen_string_literal: true

require 'tmpdir'
require 'sequel'
require_relative '../lib/video_encoder/project_removal'

RSpec.describe VideoEncoder::ProjectRemoval do
  around do |example|
    Dir.mktmpdir do |directory|
      @root = directory
      @project = File.join(directory, 'Film.json')
      @output = File.join(directory, 'Film.mkv')
      @source = File.join(directory, 'source.m2t')
      @db = Sequel.sqlite
      @db.create_table(:jobs) do
        primary_key :id
        String :project_path
        String :output_path
        String :status
      end
      File.write(@project, JSON.generate(format: 'video_encoder.trim_project', version: 2,
                                         sources: [{ path: @source }], timeline: []))
      File.write(@source, 'capture')
      File.write(@output, 'encoded')
      @service = described_class.new(@db)
      example.run
    ensure
      @db&.disconnect
    end
  end

  it 'previews without removing anything and defaults to the JSON alone' do
    plan = @service.call(@project)
    expect(plan[:files]).to eq([@project])
    expect(File.exist?(@project)).to be(true)
    expect(File.exist?(File.join(@root, '.video_encoder_trash'))).to be(false)
  end

  it 'keeps sources and videos when removing only the project and preserves queue history' do
    @db[:jobs].insert(project_path: @project, output_path: @output, status: 'done')
    plan = @service.call(@project)
    recovery = @service.call(@project, token: plan[:token])
    expect(File.exist?(@project)).to be(false)
    expect(File.read(@source)).to eq('capture')
    expect(File.read(@output)).to eq('encoded')
    expect(@db[:jobs].count).to eq(1)
    manifest = JSON.parse(File.read(File.join(recovery, 'manifest.json')))
    expect(File.read(manifest.fetch(@project))).to include('video_encoder.trim_project')
  end

  it 'includes only the confirmed video and receipt dependencies' do
    receipt = "#{@output}.video_encoder-export.json"
    File.write(receipt, '{}')
    plan = @service.call(@project, dependencies: true)
    expect(plan[:files]).to contain_exactly(@project, @output, receipt)
    @service.call(@project, dependencies: true, token: plan[:token])
    expect(File.exist?(@output)).to be(false)
    expect(File.exist?(@source)).to be(true)
  end

  it 'blocks running queued and deferred projects even at execution after a preview' do
    plan = @service.call(@project)
    %w[running queued deferred].each do |status|
      @db[:jobs].delete
      @db[:jobs].insert(project_path: @project, output_path: @output, status: status)
      expect { @service.call(@project, token: plan[:token]) }.to raise_error(VideoEncoder::ProjectRemovalError)
      expect(File.exist?(@project)).to be(true)
    end
  end

  it 'rejects changed files after confirmation was prepared' do
    plan = @service.call(@project)
    File.write(@project, "#{File.read(@project)} ")
    expect { @service.call(@project, token: plan[:token]) }.to raise_error(VideoEncoder::ProjectRemovalError, /changé/)
  end

  it 'blocks a workspace and symbolic links' do
    workspace = File.join(@root, 'video_encoder_Film_workspace')
    Dir.mkdir(workspace)
    expect { @service.call(@project) }.to raise_error(VideoEncoder::ProjectRemovalError, /workspace/)
    Dir.rmdir(workspace)
    link = File.join(@root, 'link.json')
    File.symlink(@project, link)
    expect { @service.call(link) }.to raise_error(VideoEncoder::ProjectRemovalError)
  end

  it 'protects dependencies shared with other tasks or used as a source' do
    other = File.join(@root, 'other.json')
    File.write(other, JSON.generate(format: 'video_encoder.trim_project', version: 2,
                                    sources: [{ path: @output }], timeline: []))
    @db[:jobs].insert(project_path: other, output_path: File.join(@root, 'other.mkv'), status: 'done')
    expect { @service.call(@project, dependencies: true) }.to raise_error(VideoEncoder::ProjectRemovalError, /source/)
    expect(@service.call(@project)[:files]).to eq([@project])
  end

  it 'restores already moved files if another move fails' do
    plan = @service.call(@project, dependencies: true)
    allow(File).to receive(:rename).and_call_original
    allow(File).to receive(:rename).with(@output, anything).and_raise(Errno::EXDEV)
    expect { @service.call(@project, dependencies: true, token: plan[:token]) }.to raise_error(Errno::EXDEV)
    expect(File.exist?(@project)).to be(true)
    expect(File.exist?(@output)).to be(true)
  end
end
