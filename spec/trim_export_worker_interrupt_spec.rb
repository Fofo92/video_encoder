# frozen_string_literal: true

require 'rbconfig'
require 'timeout'
require 'tmpdir'
require 'spec_helper'

RSpec.describe 'trim export worker interruption' do
  it 'persists the interrupted status after SIGINT' do
    Dir.mktmpdir(
      'video_encoder_interrupt_test'
    ) do |directory|
      database_path = File.join(
        directory,
        'video_encoder.db'
      )
      database = VideoEncoder::Persistence::Database.connect(
        database_path
      )
      repo = VideoEncoder::Persistence::JobRepository.new(database)
      job = VideoEncoder::TrimExportJob.new(
        project_path: 'movie.json',
        output_path: 'movie.mkv'
      )
      repo.enqueue(job)

      process_id = Process.spawn(
        RbConfig.ruby,
        '-Ilib',
        '-e',
        worker_script,
        database_path,
        pgroup: true,
        out: File::NULL,
        err: File::NULL
      )

      begin
        wait_until_running(repo, job)
        Process.kill('INT', -process_id)

        Timeout.timeout(5) do
          Process.wait(process_id)
        end

        stored_job = repo.find(job.id)

        expect(stored_job).to be_interrupted
        expect(stored_job.error).to eq(
          'trim export interrupted'
        )
        expect(stored_job.finished_at).not_to be_nil
      ensure
        terminate_process_group(process_id)
        database.disconnect
      end
    end
  end

  def worker_script
    <<~RUBY
      require 'logger'
      require 'rbconfig'
      require 'video_encoder'

      database =
        VideoEncoder::Persistence::Database.connect(
          ARGV.fetch(0)
        )
      repo =
        VideoEncoder::Persistence::JobRepository.new(
          database
        )

      executor = Object.new
      executor.define_singleton_method(:call) do |_job|
        VideoEncoder::CommandRunner.new.run(
          RbConfig.ruby,
          '-e',
          'sleep 30'
        )
      end

      worker = VideoEncoder::TrimExportWorker.new(
        repo: repo,
        executor: executor,
        logger: Logger.new(File::NULL)
      )

      worker.run_once
    RUBY
  end

  def wait_until_running(repo, job)
    Timeout.timeout(5) do
      loop do
        break if repo.find(job.id).running?

        sleep 0.05
      end
    end
  end

  def terminate_process_group(process_id)
    Process.kill('KILL', -process_id)
  rescue Errno::ESRCH
    nil
  ensure
    begin
      Process.wait(process_id)
    rescue Errno::ECHILD
      nil
    end
  end
end
