# frozen_string_literal: true

require 'securerandom'
require 'pathname'
require 'time'

module VideoEncoder
  # Represents a video encoding job
  class Job
    attr_reader :id,
                :source,
                :status,
                :created_at,
                :attempts,
                :started_at,
                :finished_at,
                :error

    def initialize(source:, **kwargs)
      id = kwargs.fetch(:id, nil)
      status = kwargs.fetch(:status, Status::QUEUED)
      attempts = kwargs.fetch(:attempts, 0)
      created_at = kwargs.fetch(:created_at, Time.now)
      started_at = kwargs.fetch(:started_at, nil)
      finished_at = kwargs.fetch(:finished_at, nil)
      error = kwargs.fetch(:error, nil)

      @id = id || SecureRandom.uuid
      @source = Pathname.new(source)
      @status = status
      @attempts = attempts

      @created_at = created_at
      @started_at = started_at
      @finished_at = finished_at
      @error = error
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

    def with_source(source)
      self.class.new(
        id: id,
        source: source,
        status: status,
        attempts: attempts,
        created_at: created_at,
        started_at: started_at,
        finished_at: finished_at,
        error: error
      )
    end
    
    private

    def now
      Time.now
    end
  end
end
