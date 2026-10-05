# frozen_string_literal: true

require_relative 'cli/export_command'
require_relative 'cli/config_command'
require_relative 'cli/preflight_audio_command'
require_relative 'cli/job_presenter'
require_relative 'cli/job_serializer'
require_relative 'cli/source_usage_command'
require_relative 'cli/quarantine_source_command'
require_relative 'cli/list_jobs_command'
require_relative 'cli/enqueue_trim_export_command'
require_relative 'cli/run_trim_exports_command'
require_relative 'cli/inspect_media_command'

module VideoEncoder
  # CLI handles command-line interface for VideoEncoder.

  COMMANDS = {
    'version' => :print_version,
    'enqueue-trim-export' => :enqueue_trim_export,
    'remove-job' => :remove_job,
    'list' => :list,
    'status' => :status,
    'failed' => :failed,
    'run-trim-exports' => :run_trim_exports,
    'config' => :show_config,
    'export' => :export_trim_project,
    'preflight-audio' => :preflight_audio,
    'inspect-media' => :inspect_media,
    'source-usage' => :show_source_usage,
    'quarantine-source' => :quarantine_source
  }.freeze

  CLI_USAGE = <<~TEXT
    Usage:
      video_encoder version
      video_encoder run-trim-exports [--once]
      video_encoder enqueue-trim-export <project.json> --output <movie.mkv>
      video_encoder remove-job <job_id>
      video_encoder list [--json]
      video_encoder status <job_id>
      video_encoder config
      video_encoder export <project.json> --output <movie.mkv>
      video_encoder preflight-audio <project.json>
      video_encoder inspect-media <file>
      video_encoder source-usage <source>
      video_encoder failed
      video_encoder quarantine-source <source> --confirm
  TEXT

  # Provides the command-line interface for VideoEncoder.
  class CLI
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

    def preflight_audio
      PreflightAudioCommand.new(argv: @argv, dependency_checker:).run
    end

    def inspect_media
      InspectMediaCommand.new(argv: @argv, dependency_checker:).run
    end

    def show_source_usage
      SourceUsageCommand.build(argv: @argv, repo: repo).run
    end

    def quarantine_source
      QuarantineSourceCommand.build(argv: @argv, repo: repo, config: config).run
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
      ListJobsCommand.new(
        argv: @argv,
        repo: repo
      ).run
    end

    def enqueue_trim_export
      EnqueueTrimExportCommand.new(argv: @argv, repo: repo).run
    end

    def remove_job
      id = @argv.shift or abort('Usage: remove-job <job_id>')

      return puts("Removed queued job: #{id}") if repo.remove_queued?(id)

      job = repo.find(id)
      abort("Job not found: #{id}") unless job

      abort("Job is not queued: #{id}")
    end

    def status
      id = @argv.shift or abort('Usage: status <job_id>')

      job = repo.find(id)
      return puts('Job not found') unless job

      puts job_presenter.details(job)
    end

    def job_presenter
      @job_presenter ||= JobPresenter.new
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
        puts job_presenter.failure(job)
      end
    end

    def run_trim_exports
      RunTrimExportsCommand.new(
        argv: @argv,
        repo: repo,
        dependency_checker: dependency_checker,
        command_probe: command_probe
      ).run
    end

    def show_config
      ConfigCommand.new(config: config).run
    end

    def usage
      CLI_USAGE
    end
  end
end
