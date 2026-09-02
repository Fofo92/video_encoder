# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI::EnqueueTrimExportCommand do
  let(:file) { class_double(File) }
  let(:repo) do
    instance_double(
      VideoEncoder::Persistence::JobRepository
    )
  end

  describe '#run' do
    before do
      allow(file).to receive(:file?)
        .with('movie.json')
        .and_return(true)

      allow(file).to receive(:exist?)
        .with('movie.mkv')
        .and_return(false)
    end

    it 'enqueues a trim export job' do
      job = nil

      allow(repo).to receive(:enqueue) do |value|
        job = value
      end

      command = described_class.new(
        argv: [
          'movie.json',
          '--output',
          'movie.mkv'
        ],
        repo: repo,
        file: file
      )

      expect { command.run }
        .to output(
          /Enqueued trim export: .+ \(movie\.json -> movie\.mkv\)/
        )
        .to_stdout

      expect(job).to be_a(
        VideoEncoder::TrimExportJob
      )
      expect(job.project_path).to eq(
        Pathname('movie.json')
      )
      expect(job.output_path).to eq(
        Pathname('movie.mkv')
      )
      expect(repo).to have_received(:enqueue)
        .with(job)
        .once
    end

    it 'rejects invalid arguments' do
      command = described_class.new(
        argv: ['movie.json'],
        repo: repo,
        file: file
      )

      expect { command.run }
        .to raise_error(
          SystemExit,
          'Usage: video_encoder enqueue-trim-export ' \
          '<project.json> --output <movie.mkv>'
        )
    end

    it 'rejects a missing project file' do
      allow(file).to receive(:file?)
        .with('movie.json')
        .and_return(false)

      command = described_class.new(
        argv: [
          'movie.json',
          '--output',
          'movie.mkv'
        ],
        repo: repo,
        file: file
      )

      expect(repo).not_to receive(:enqueue)

      expect { command.run }
        .to raise_error(
          SystemExit,
          'project file not found: movie.json'
        )
    end

    it 'refuses an existing output file' do
      allow(file).to receive(:exist?)
        .with('movie.mkv')
        .and_return(true)

      command = described_class.new(
        argv: [
          'movie.json',
          '--output',
          'movie.mkv'
        ],
        repo: repo,
        file: file
      )

      expect(repo).not_to receive(:enqueue)

      expect { command.run }
        .to raise_error(
          SystemExit,
          'output already exists: movie.mkv'
        )
    end
  end
end
