# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'
require 'fileutils'

RSpec.describe VideoEncoder::Watcher do
  let(:repo) { instance_double(VideoEncoder::Persistence::JobRepository) }

  let(:tmpdir) { Dir.mktmpdir }

  after do
    FileUtils.remove_entry(tmpdir)
  end
  let(:incoming) { File.join(tmpdir, 'incoming') }
  let(:queue)    { File.join(tmpdir, 'queue') }

  let(:watcher) do
    described_class.new(
      incoming: incoming,
      queue: queue,
      repo: repo
    )
  end

  before do
    FileUtils.mkdir_p(incoming)
    FileUtils.mkdir_p(queue)

    allow(repo).to receive(:enqueue)
  end

  it 'does not enqueue a file the first time it sees it' do
    create_video

    watcher.scan_once

    expect(repo).not_to have_received(:enqueue)
  end

  it 'enqueues a file the second time it sees it unchanged' do
    create_video

    watcher.scan_once
    watcher.scan_once

    expect(repo).to have_received(:enqueue)
  end

  it 'moves the file to the queue directory' do
    file_path = create_video

    watcher.scan_once
    watcher.scan_once

    queued_file = File.join(queue, File.basename(file_path))

    expect(File).not_to exist(file_path)
    expect(File).to exist(queued_file)
  end

  it 'does not enqueue the same file twice' do
    file_path = File.join(incoming, 'video.mp4')
    File.write(file_path, 'dummy content')

    watcher.scan_once
    watcher.scan_once
    watcher.scan_once

    expect(repo).to have_received(:enqueue).once
  end

  it 'waits until the file size stops changing' do
    file_path = create_video

    watcher.scan_once

    File.write(file_path, 'abcdef')

    watcher.scan_once

    expect(repo).not_to have_received(:enqueue)

    watcher.scan_once

    expect(repo).to have_received(:enqueue).once
  end

  private

  def create_video(name = 'video.mp4', content = 'dummy content')
    path = File.join(incoming, name)
    File.write(path, content)
    path
  end
end
