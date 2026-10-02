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

  describe 'list' do
    let(:repo) { instance_double(VideoEncoder::Persistence::JobRepository) }

    let(:job) do
      VideoEncoder::TrimExportJob.new(
        id: '123',
        project_path: 'movie.json',
        output_path: 'movie.mkv',
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
          /123 \| trim_export \| movie\.json \| movie\.mkv \| queued \| attempts=0/
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
      VideoEncoder::TrimExportJob.new(
        id: '123',
        project_path: 'movie.json',
        output_path: 'movie.mkv',
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
          /ID:\s+123.*Type:\s+trim_export.*Input:\s+movie\.json.*Output:\s+movie\.mkv.*Status:\s+done.*Attempts:\s+1/m
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
        VideoEncoder::TrimExportJob.new(
          id: '123',
          project_path: 'movie.json',
          output_path: 'movie.mkv',
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
          .to output(/123.*movie\.json.*attempts=2.*boom/m)
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

  describe 'config' do
    it 'prints the application configuration' do
      cli = described_class.new(['config'])

      expect { cli.run }
        .to output(
          a_string_including(
            'Database:',
            'Quarantine:',
            'FFmpeg',
            'Video codec:',
            'Audio codec:',
            'Preset:',
            'CQ:'
          )
        ).to_stdout
    end
  end
end
