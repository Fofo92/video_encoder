# frozen_string_literal: true

require 'pathname'
require 'securerandom'
require 'time'

module VideoEncoder
  # Represents an export of a prepared trim project.
  class TrimExportJob
    KIND = 'trim_export'

    attr_reader :id,
                :project_path,
                :output_path,
                :status,
                :created_at,
                :attempts,
                :started_at,
                :finished_at,
                :error

    def initialize(project_path:, output_path:, **kwargs)
      @id = kwargs.fetch(:id, nil) ||
            SecureRandom.uuid
      @project_path = Pathname.new(project_path)
      @output_path = Pathname.new(output_path)
      @status = kwargs.fetch(
        :status,
        Status::QUEUED
      )
      @attempts = kwargs.fetch(:attempts, 0)
      @created_at = kwargs.fetch(
        :created_at,
        Time.now
      )
      @started_at = kwargs.fetch(
        :started_at,
        nil
      )
      @finished_at = kwargs.fetch(
        :finished_at,
        nil
      )
      @error = kwargs.fetch(:error, nil)
    end

    def kind
      KIND
    end

    def queued?
      status == Status::QUEUED
    end

    def running?
      status == Status::RUNNING
    end

    def done?
      status == Status::DONE
    end

    def failed?
      status == Status::FAILED
    end

    def start!
      @status = Status::RUNNING
      @started_at = now
      self
    end

    def finish!
      @status = Status::DONE
      @finished_at = now
      self
    end

    def fail!(message)
      @status = Status::FAILED
      @error = message
      @finished_at = now
      self
    end

    private

    def now
      Time.now
    end
  end
end
