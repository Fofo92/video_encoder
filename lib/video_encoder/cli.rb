# frozen_string_literal: true

require_relative 'cli/export_command'
require_relative 'cli/config_command'

module VideoEncoder
  # CLI handles command-line interface for VideoEncoder.

  COMMANDS = {
    'version' => :print_version,
    'enqueue' => :enqueue,
    'list' => :list,
    'status' => :status,
    'failed' => :failed,
    'run' => :run_worker,
    'config' => :show_config,
    'watch' => :watch,
    'export' => :export_trim_project
  }.freeze

  # Provides the command-line interface for VideoEncoder.
  class CLI
    # Provides the command-line interface for VideoEncoder.

    def self.start(argv, **)
      new(argv, **).run
    rescue MissingExternalDependenciesError => e
      warn e.message
      exit 1
    end

    def initialize(
      argv,
      config: VideoEncoder::Config.load,
      trim_export_service: nil,
      dependency_checker: ExternalDependencyChecker.new,
      command_probe: ExternalCommandProbe.new
    )
      @argv = argv
      @config = config
      @trim_export_service = trim_export_service
      @dependency_checker = dependency_checker
      @command_probe = command_probe
    end

    def run
      handler = COMMANDS[@argv.shift]

      return __send__(handler) if handler

      puts usage
      exit 1
    end

    private

    attr_reader :dependency_checker, :command_probe

    def print_version
      puts VideoEncoder::VERSION
    end

    def export_trim_project
      ExportCommand.new(
        argv: @argv,
        service: @trim_export_service,
        dependency_checker: @dependency_checker,
        command_probe: command_probe
      ).run
    end

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
          config: @config.ffmpeg,
          selector: track_selector,
          media_probe: media_probe
        )
      else
        VideoEncoder::Encoder::FakeEncoder.new(
          logger: logger
        )
      end
    end

    def verifier
      @verifier ||= VideoEncoder::Verifier.new(logger: logger)
    end

    def run_worker
      check_encoding_dependencies

      mode = @argv.shift

      puts 'Starting worker...'

      if mode == '--once'
        worker.run_once
      else
        puts 'Running in loop (CTRL+C to stop)'
        worker.run
      end
    end

    def check_encoding_dependencies
      return unless config.encoder == 'ffmpeg'

      dependency_checker.call(
        'ffmpeg',
        'ffprobe'
      )
    end

    def worker
      @worker ||= VideoEncoder::Worker.new(
        repo: repo,
        encoder: encoder,
        verifier: verifier,
        logger: logger,
        workspace: workspace
      )
    end

    def show_config
      ConfigCommand.new(config: config).run
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
          video_encoder config
          video_encoder watch [--once]
          video_encoder export <project.json> --output <movie.mkv>
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

    def workspace
      @workspace ||= VideoEncoder::Workspace.new(directories: @config.directories)
    end

    def track_selector
      @track_selector ||= VideoEncoder::TrackSelector.new
    end

    def media_probe
      @media_probe ||= VideoEncoder::MediaProbe.new
    end
  end
end
