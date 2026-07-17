# frozen_string_literal: true

require 'open3'

RSpec.describe VideoEncoder::CLI do
  it 'prints version' do
    stdout, _stderr, status = Open3.capture3('bin/video_encoder version')

    expect(status.success?).to eq(true)
    expect(stdout.strip).to eq(VideoEncoder::VERSION)
  end

  it 'shows usage for unknown command' do
    stdout, _stderr, status = Open3.capture3('bin/video_encoder unknown')

    expect(status.success?).to eq(false)
    expect(stdout).to include('Usage')
  end

  describe 'enqueue' do
    let(:repo) { instance_double(VideoEncoder::Persistence::JobRepository) }

    before do
      allow(VideoEncoder::Persistence::JobRepository)
        .to receive(:new)
        .and_return(repo)

      allow(repo).to receive(:enqueue)
    end

    it 'enqueues a job' do
      cli = described_class.new(['enqueue', 'video.mp4'])

      cli.run

      expect(repo).to have_received(:enqueue)
    end
  end

  describe 'list' do
    let(:repo) { instance_double(VideoEncoder::Persistence::JobRepository) }

    let(:job) do
      VideoEncoder::Job.new(
        id: '123',
        source: 'video.mp4',
        status: VideoEncoder::Status::QUEUED,
        attempts: 0
      )
    end

    before do
      allow(VideoEncoder::Persistence::JobRepository)
        .to receive(:new)
        .and_return(repo)

      allow(repo).to receive(:all).and_return([job])
    end

    it 'prints the list of jobs' do
      cli = described_class.new(['list'])

      expect { cli.run }
        .to output(
          /123 \| video\.mp4 \| queued \| attempts=0/
        ).to_stdout
    end

    context 'when there are no jobs' do
      before do
        allow(repo).to receive(:all).and_return([])
      end

      it 'prints a message' do
        cli = described_class.new(['list'])

        expect { cli.run }
          .to output(/No jobs found/).to_stdout
      end
    end
  end

  describe 'status' do
    let(:repo) { instance_double(VideoEncoder::Persistence::JobRepository) }

    let(:job) do
      VideoEncoder::Job.new(
        id: '123',
        source: 'video.mp4',
        status: VideoEncoder::Status::DONE,
        attempts: 1
      )
    end

    before do
      allow(VideoEncoder::Persistence::JobRepository)
        .to receive(:new)
        .and_return(repo)
    end

    it 'prints the job status' do
      allow(repo).to receive(:find).with('123').and_return(job)

      cli = described_class.new(%w[status 123])

      expect { cli.run }
        .to output(
          /ID:\s+123.*Source:\s+video\.mp4.*Status:\s+done.*Attempts:\s+1/m
        ).to_stdout
    end

    it 'prints a message when the job does not exist' do
      allow(repo).to receive(:find).with('123').and_return(nil)

      cli = described_class.new(%w[status 123])

      expect { cli.run }
        .to output(/Job not found/).to_stdout
    end

    it 'aborts when no job id is given' do
      cli = described_class.new(['status'])

      expect { cli.run }
        .to raise_error(SystemExit)
    end
  end

  describe 'failed' do
    let(:repo) { instance_double(VideoEncoder::Persistence::JobRepository) }

    before do
      allow(VideoEncoder::Persistence::JobRepository)
        .to receive(:new)
        .and_return(repo)
    end

    context 'when there are failed jobs' do
      let(:failed_job) do
        VideoEncoder::Job.new(
          id: '123',
          source: 'video.mp4',
          status: VideoEncoder::Status::FAILED,
          attempts: 2,
          error: 'boom'
        )
      end

      before do
        allow(repo).to receive(:all).and_return([failed_job])
      end

      it 'prints the failed jobs' do
        cli = described_class.new(['failed'])

        expect { cli.run }
          .to output(/123.*video\.mp4.*attempts=2.*boom/m)
          .to_stdout
      end
    end

    context 'when there are no failed jobs' do
      before do
        allow(repo).to receive(:all).and_return([])
      end

      it 'prints a message' do
        cli = described_class.new(['failed'])

        expect { cli.run }
          .to output(/No failed jobs/)
          .to_stdout
      end
    end
  end

  describe 'run' do
    let(:worker) { instance_double(VideoEncoder::Worker) }

    before do
      allow(VideoEncoder::Worker)
        .to receive(:new)
        .and_return(worker)

      allow(worker).to receive(:run_once)
      allow(worker).to receive(:run)
    end

    it 'runs the worker once' do
      cli = described_class.new(['run', '--once'])

      cli.run

      expect(worker).to have_received(:run_once)
      expect(worker).not_to have_received(:run)
    end

    it 'runs the worker in loop mode by default' do
      cli = described_class.new(['run'])

      cli.run

      expect(worker).to have_received(:run)
      expect(worker).not_to have_received(:run_once)
    end

    describe 'config' do
      it 'prints the application configuration' do
        cli = described_class.new(['config'])

        expect { cli.run }
          .to output(
            a_string_including(
              'Database:',
              'Encoder:',
              'Incoming:',
              'Queue:',
              'Encoded:',
              'Archive:',
              'FFmpeg',
              'Video codec:',
              'Audio codec:',
              'Preset:',
              'CQ:'
            )
          ).to_stdout
      end
    end

    describe 'watch' do
      let(:watcher) { instance_double(VideoEncoder::Watcher) }

      before do
        allow(VideoEncoder::Watcher)
          .to receive(:new)
          .and_return(watcher)

        allow(watcher).to receive(:scan_once)
      end

      it 'runs the watcher once' do
        cli = described_class.new(%w[watch --once])

        cli.run

        expect(watcher).to have_received(:scan_once)
      end
    end
  end
end
