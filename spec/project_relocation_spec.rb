# frozen_string_literal: true

require 'tmpdir'
require 'fileutils'
require 'sequel'
require_relative '../lib/video_encoder/project_relocation'
require_relative '../lib/video_encoder/domain/status'
require_relative '../lib/video_encoder/domain/trim_export_job'
require_relative '../lib/video_encoder/persistence/job_repository'
require_relative '../lib/video_encoder/trim_export_worker'

RSpec.shared_context 'project relocation files' do
  around do |example|
    Dir.mktmpdir do |directory|
      @root = directory
      @old = File.join(directory, 'old')
      @new = File.join(directory, 'new')
      FileUtils.mkdir_p([@old, @new])
      @project = File.join(@old, 'Film & suite.json')
      @output = File.join(@old, 'Film & suite.mkv')
      @db = Sequel.sqlite
      @db.create_table(:jobs) do
        primary_key :id
        String :job_id
        String :kind
        Integer :attempts, default: 0
        Integer :worker_pid
        DateTime :started_at
        DateTime :finished_at
        DateTime :created_at
        String :error
        String :project_path
        String :output_path
        String :status
      end
      File.write(@project, JSON.generate(format: 'video_encoder.trim_project', version: 2,
                                         sources: [{ id: 'source', path: '/captures/source.m2t' }], timeline: []))
      @db[:jobs].insert(project_path: @project, output_path: @output, status: 'done')
      example.run
    ensure
      @db&.disconnect
    end
  end

  def move_project
    described_class.new(@db).call(@project, @new)
  end
end

RSpec.describe VideoEncoder::ProjectRelocation do
  include_context 'project relocation files'

  it 'moves a project, its video and receipt while updating every associated job' do
    File.binwrite(@output, 'encoded video')
    mtime = Time.at(1_700_000_000)
    File.utime(mtime, mtime, @output)
    receipt = "#{@output}.video_encoder-export.json"
    File.write(receipt, JSON.generate(format: 'video_encoder.completed_export', version: 1,
                                      project_path: @project, output_path: @output,
                                      project_sha256: Digest::SHA256.file(@project).hexdigest))
    @db[:jobs].insert(project_path: @project, output_path: @output, status: 'queued')
    destination = move_project
    expect(destination).to eq(File.join(@new, File.basename(@project)))
    expect(File.exist?(@project)).to be(false)
    expect(File.exist?(@output)).to be(false)
    expect(File.binread(File.join(@new, File.basename(@output)))).to eq('encoded video')
    expect(File.mtime(File.join(@new, File.basename(@output)))).to eq(mtime)
    expect(@db[:jobs].select_map(:project_path).uniq).to eq([destination])
    expect(@db[:jobs].select_map(:status)).to eq(%w[done queued])
    moved_receipt = JSON.parse(File.read(File.join(@new, File.basename(receipt))))
    expect(moved_receipt['output_path']).to eq(File.join(@new, File.basename(@output)))
    expect(moved_receipt['previous_output_path']).to eq(@output)
    expect(moved_receipt['project_sha256']).to eq(Digest::SHA256.file(destination).hexdigest)
  end

  it 'does not falsely certify a project that was modified after its video was encoded' do
    File.binwrite(@output, 'video from an earlier project')
    receipt = "#{@output}.video_encoder-export.json"
    File.write(receipt, JSON.generate(format: 'video_encoder.completed_export', version: 1,
                                      project_sha256: 'older-project-hash'))
    move_project
    moved = JSON.parse(File.read(File.join(@new, File.basename(receipt))))
    expect(moved['project_sha256']).to eq('older-project-hash')
  end

  it 'ignores historical jobs without project or output paths' do
    @db[:jobs].insert(kind: 'legacy', status: 'done')
    expect(File.file?(move_project)).to be(true)
  end

  it 'also moves a project that has no job or encoded output yet' do
    @db[:jobs].delete
    expect(File.file?(move_project)).to be(true)
    expect(@db[:jobs].count).to eq(0)
  end

  it 'keeps a relative source reference anchored to the same existing loader path' do
    text = JSON.parse(File.read(@project))
    text['sources'][0]['path'] = 'captures/source.m2t'
    File.write(@project, JSON.generate(text))
    result = JSON.parse(File.read(move_project))
    expect(result['sources'][0]['path']).to eq(File.expand_path('captures/source.m2t'))
  end

  it 'supports version one references without changing the frame boundaries' do
    File.write(@project, JSON.generate(format: 'video_encoder.trim_project', version: 1,
                                       timeline: [{ type: 'segment', source: 'source.m2t',
                                                    start_frame: 4, end_frame: 10 }]))
    segment = JSON.parse(File.read(move_project))['timeline'].first
    expect(segment).to include('start_frame' => 4, 'end_frame' => 10,
                               'source' => File.expand_path('source.m2t'))
  end

  it 'does not move a capture used as the project source even when its name resembles an output' do
    File.write(@output, 'source capture')
    document = JSON.parse(File.read(@project))
    document['sources'][0]['path'] = @output
    File.write(@project, JSON.generate(document))
    move_project
    expect(File.read(@output)).to eq('source capture')
  end

  it 'refuses a project being encoded and changes neither its paths nor its files' do
    @db[:jobs].update(status: 'running')
    expect { move_project }.to raise_error(VideoEncoder::ProjectRelocationError, /encodage/)
    expect(File.file?(@project)).to be(true)
    expect(Dir.children(@new)).to be_empty
  end

  it 'refuses an existing destination without overwriting its contents' do
    File.write(File.join(@new, File.basename(@project)), 'keep')
    expect { move_project }.to raise_error(VideoEncoder::ProjectRelocationError, /présente/)
    expect(File.read(File.join(@new, File.basename(@project)))).to eq('keep')
    expect(File.file?(@project)).to be(true)
  end

  it 'rejects another project using one of the output destinations' do
    @db[:jobs].insert(project_path: '/other.json', output_path: File.join(@new, File.basename(@output)),
                      status: 'queued')
    expect { move_project }.to raise_error(VideoEncoder::ProjectRelocationError, /référencée/)
    expect(Dir.children(@new)).to be_empty
  end

  it 'rejects a remaining workspace rather than abandoning resume data' do
    FileUtils.mkdir_p(File.join(@old, 'video_encoder_Film & suite_workspace'))
    expect { move_project }.to raise_error(VideoEncoder::ProjectRelocationError, /workspace/)
    expect(File.file?(@project)).to be(true)
  end

  it 'copies safely when the destination is on another filesystem' do
    File.write(@output, 'cross-volume video')
    allow(File).to receive(:link).and_raise(Errno::EXDEV)
    destination = move_project
    expect(File.file?(destination)).to be(true)
    expect(File.read(File.join(@new, File.basename(@output)))).to eq('cross-volume video')
    expect(File.exist?(@output)).to be(false)
  end

  it 'refuses symlinks without relocating their target' do
    alias_path = File.join(@old, 'alias.json')
    File.symlink(@project, alias_path)
    expect { described_class.new(@db).call(alias_path, @new) }.to raise_error(VideoEncoder::ProjectRelocationError)
    expect(File.file?(@project)).to be(true)
  end

  it 'lets a worker reload the relocated paths even if it selected the job before the move' do
    @db[:jobs].update(job_id: 'race', kind: 'trim_export', status: 'queued')
    repo = VideoEncoder::Persistence::JobRepository.new(@db)
    stale = repo.next
    destination = move_project
    allow(repo).to receive(:next).and_return(stale, nil)
    executor = double('executor', call: nil)
    worker = VideoEncoder::TrimExportWorker.new(repo: repo, executor: executor, logger: double('logger', info: nil))
    worker.run_once
    expect(executor).to have_received(:call) do |job|
      expect(job.project_path.to_s).to eq(destination)
    end
    expect(@db[:jobs].first[:status]).to eq('done')
  end

  it 'rolls back copies and job paths if the database update fails' do
    @db.run("CREATE TRIGGER reject_move BEFORE UPDATE ON jobs BEGIN SELECT RAISE(ABORT, 'database failure'); END")
    expect { move_project }.to raise_error(Sequel::DatabaseError, /database failure/)
    expect(File.file?(@project)).to be(true)
    expect(Dir.children(@new)).to be_empty
    expect(@db[:jobs].first[:project_path]).to eq(@project)
  end
end

RSpec.describe VideoEncoder::ProjectRelocation, 'renaming' do
  include_context 'project relocation files'

  it 'renames the project video and receipt in the same directory without changing cuts or binding' do
    document = JSON.parse(File.read(@project))
    document['project_id'] = 'stable-id'
    document['vidb'] = { 'record_id' => 42, 'binding_token' => 'stable-token' }
    document['timeline'] = [{ 'type' => 'segment', 'source_id' => 'source', 'start_frame' => 4, 'end_frame' => 123 }]
    File.write(@project, JSON.generate(document))
    File.write(@output, 'video')
    receipt_document = { format: 'video_encoder.completed_export', version: 1,
                         project_path: @project, output_path: @output, project_id: 'stable-id',
                         project_sha256: Digest::SHA256.file(@project).hexdigest,
                         probe: { format: { filename: @output } } }
    File.write("#{@output}.video_encoder-export.json", JSON.generate(receipt_document))
    destination = described_class.new(@db).call(@project, @old, name: 'Épisode : A & B')
    video = File.join(@old, 'Épisode : A & B.mkv')
    expect(destination).to eq(File.join(@old, 'Épisode : A & B.json'))
    expect(JSON.parse(File.read(destination))).to eq(document)
    expect(File.read(video)).to eq('video')
    expect(File.exist?(@project)).to be(false)
    expect(File.exist?(@output)).to be(false)
    receipt = JSON.parse(File.read("#{video}.video_encoder-export.json"))
    expect(receipt).to include('project_path' => destination, 'output_path' => video, 'project_id' => 'stable-id')
    expect(receipt.dig('probe', 'format', 'filename')).to eq(video)
    expect(receipt['project_sha256']).to eq(Digest::SHA256.file(destination).hexdigest)
    expect(@db[:jobs].first).to include(project_path: destination, output_path: video, status: 'done')
  end

  it 'previews every existing file without changing files or the queue' do
    File.write(@output, 'video')
    before = @db[:jobs].all
    plan = described_class.new(@db).call(@project, @old, name: 'Nouveau', preview: true)
    expect(plan[:project_path]).to eq(File.join(@old, 'Nouveau.json'))
    expect(plan[:files]).to include(source: @output, destination: File.join(@old, 'Nouveau.mkv'))
    expect(@db[:jobs].all).to eq(before)
    expect(Dir.children(@old).sort).to eq(['Film & suite.json', 'Film & suite.mkv'])
    expect(@db.in_transaction?).to be(false)
  end

  it 'renames and relocates together including an output that does not exist yet' do
    destination = described_class.new(@db).call(@project, @new, name: 'Nouveau')
    expect(File.file?(destination)).to be(true)
    expect(@db[:jobs].first[:output_path]).to eq(File.join(@new, 'Nouveau.mkv'))
    expect(File.exist?(File.join(@new, 'Nouveau.mkv'))).to be(false)
  end

  it 'rejects unsafe or empty names without changing anything' do
    ['', ' ', '..', '../film', 'film/suite', 'film\\suite', "film\n", 'film.json'].each do |name|
      expect { described_class.new(@db).call(@project, @old, name: name) }
        .to raise_error(VideoEncoder::ProjectRelocationError)
    end
    expect(File.file?(@project)).to be(true)
    expect(@db[:jobs].first[:project_path]).to eq(@project)
  end

  it 'rejects an occupied new name in preview and execution' do
    target = File.join(@old, 'Nouveau.mkv')
    File.write(target, 'keep')
    [true, false].each do |preview|
      expect { described_class.new(@db).call(@project, @old, name: 'Nouveau', preview: preview) }
        .to raise_error(VideoEncoder::ProjectRelocationError, /présente/)
    end
    expect(File.read(target)).to eq('keep')
    expect(File.file?(@project)).to be(true)
  end

  it 'rechecks running jobs when executing a previously valid preview' do
    described_class.new(@db).call(@project, @old, name: 'Nouveau', preview: true)
    @db[:jobs].update(status: 'running')
    expect { described_class.new(@db).call(@project, @old, name: 'Nouveau') }
      .to raise_error(VideoEncoder::ProjectRelocationError, /encodage/)
    expect(File.file?(@project)).to be(true)
  end

  it 'rolls back renamed files when the queue cannot be updated' do
    File.write(@output, 'video')
    @db.run("CREATE TRIGGER reject_move BEFORE UPDATE ON jobs BEGIN SELECT RAISE(ABORT, 'database failure'); END")
    expect { described_class.new(@db).call(@project, @old, name: 'Nouveau') }.to raise_error(Sequel::DatabaseError)
    expect(Dir.children(@old).sort).to eq(['Film & suite.json', 'Film & suite.mkv'])
    expect(@db[:jobs].first[:project_path]).to eq(@project)
  end
  it 'refuses to merge distinct queued outputs under one renamed path' do
    @db[:jobs].insert(project_path: @project, output_path: File.join(@old, 'Other.mkv'), status: 'queued')
    expect { described_class.new(@db).call(@project, @old, name: 'Nouveau') }
      .to raise_error(VideoEncoder::ProjectRelocationError, /sorties distinctes/)
    expect(File.file?(@project)).to be(true)
    expect(@db[:jobs].select_map(:project_path).uniq).to eq([@project])
  end
end
