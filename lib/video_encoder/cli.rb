# frozen_string_literal: true

module VideoEncoder
  # CLI handles command-line interface for VideoEncoder.
  class CLI
    def self.start(argv)
      new(argv).run
    end

    def initialize(argv)
      @argv = argv
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

      else
        puts usage
        exit 1
      end
    end

    private

    def config
      @config ||= VideoEncoder::Configuration.load
    end

    def repo
      @repo ||= VideoEncoder::Persistence::JobRepository.new(
        VideoEncoder::Persistence::Database.connect(config.database)
      )
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
      config.logger
    end

    def encoder
      @encoder ||=
        if config.encoder == 'ffmpeg'
          VideoEncoder::Encoder::FFmpegEncoder.new(logger: logger)
        else
          VideoEncoder::Encoder::FakeEncoder.new(logger: logger)
        end
    end

    def usage
      <<~TEXT
        Usage:
          video_encoder version
          video_encoder enqueue <file>
          video_encoder list
          video_encoder status <job_id>
          video_encoder failed
      TEXT
    end
  end
end
