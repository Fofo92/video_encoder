# frozen_string_literal: true

module VideoEncoder
  # CLI handles command-line interface for VideoEncoder.
  class CLI
    def self.start(argv)
      new(argv).run
    end

    def initialize(argv, config: VideoEncoder::Config.load)
      @argv = argv
      @config = config
    end

    def run
      command = @argv.shift

      case command
      when 'version'
        puts VideoEncoder::VERSION

      when 'enqueue'
        enqueue

      when 'list'
        list

      when 'status'
        status

      when 'failed'
        failed

      when 'run'
        run_worker

      when 'config'
        show_config

      when 'watch'
        watch

      else
        puts usage
        exit 1
      end
    end

    private

    def config
      @config
    end

    def database
      @database ||= VideoEncoder::Persistence::Database.connect(
        config.database
      )
    end

    def repo
      @repo ||= VideoEncoder::Persistence::JobRepository.new(database)
    end

    def list
      jobs = repo.all

      puts 'ID | SOURCE | STATUS'
      puts '-' * 60

      return puts 'No jobs found' if jobs.empty?

      jobs.each do |job|
        puts "#{job.id} | #{job.source} | #{job.status} | attempts=#{job.attempts}"
      end
    end

    def enqueue
      file = @argv.shift or abort('Usage: enqueue <file>')

      job = VideoEncoder::Job.new(source: file)

      repo.enqueue(job)

      puts "Enqueued: #{job.id} (#{file})"
    end

    def status
      id = @argv.shift or abort('Usage: status <job_id>')

      job = repo.find(id)
      return puts('Job not found') unless job

      print_job_status(job)
    end

    def print_job_status(job)
      puts "ID:       #{job.id}"
      puts "Source:   #{job.source}"
      puts "Status:   #{job.status}"
      puts "Attempts: #{job.attempts}"
      puts "Created:  #{job.created_at}"
      puts "Started:  #{job.started_at}"
      puts "Finished: #{job.finished_at}"
      puts "Error:    #{job.error}"
    end

    def failed
      jobs = repo.all.select(&:failed?)

      if jobs.empty?
        puts 'No failed jobs'
        return
      end

      puts 'FAILED JOBS'
      puts '-' * 60

      jobs.each do |job|
        puts "#{job.id} | #{job.source} | attempts=#{job.attempts} | error=#{job.error}"
      end
    end

    def logger
      @logger ||= Logger.new($stdout)
    end

    def encoder
      @encoder ||= if config.encoder == "ffmpeg"
        VideoEncoder::Encoder::FFmpegEncoder.new(
          logger: logger,
          config: config.ffmpeg
        )
      else
        VideoEncoder::Encoder::FakeEncoder.new(
          logger: logger
        )
      end
    end

    def run_worker
      mode = @argv.shift

      puts 'Starting worker...'

      if mode == '--once'
        worker.run_once
      else
        puts 'Running in loop (CTRL+C to stop)'
        worker.run
      end
    end

    def worker
      @worker ||= VideoEncoder::Worker.new(
        repo: repo,
        encoder: encoder,
        logger: logger,
        config: config
      )
    end

    def show_config
      puts "Database: #{config.database}"
      puts "Encoder:  #{config.encoder}"
      puts

      puts 'Directories'
      puts '-----------'
      puts "Incoming: #{config.directories.incoming}"
      puts "Queue:    #{config.directories.queue}"
      puts "Encoded:  #{config.directories.encoded}"
      puts "Archive:  #{config.directories.archive}"
      puts
      puts 'FFmpeg'
      puts '-------'
      puts "Container:   #{config.ffmpeg.container}"
      puts "Video codec: #{config.ffmpeg.video_codec}"
      puts "Preset:      #{config.ffmpeg.preset}"
      puts "Tune:        #{config.ffmpeg.tune}"
      puts "RC:          #{config.ffmpeg.rc}"
      puts "CQ:          #{config.ffmpeg.cq}"
      puts "Audio codec: #{config.ffmpeg.audio_codec}"
    end

    def watch
      mode = @argv.shift

      puts 'Starting watcher...'

      if mode == '--once'
        watcher.scan_once
      else
        puts "Watching #{config.directories.incoming} (CTRL+C to stop)"

        loop do
          watcher.scan_once
          sleep 1
        end
      end
    end

    def usage
      <<~TEXT
        Usage:
          video_encoder version
          video_encoder enqueue <file>
          video_encoder run [--once]
          video_encoder list
          video_encoder status <job_id>
          video_encoder failed
      TEXT
    end

    def watcher
      @watcher ||= VideoEncoder::Watcher.new(
        incoming: config.directories.incoming,
        queue: config.directories.queue,
        repo: repo
      )
    end
  end
end
