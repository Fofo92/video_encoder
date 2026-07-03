# frozen_string_literal: true

require 'pathname'
require 'time'

module VideoEncoder
  # Represents a video encoding job
  class Job
    attr_reader :id,
                :source,
                :status,
                :created_at,
                :started_at,
                :finished_at,
                :error

    def initialize(source:, id: SecureRandom.uuid, status: Status::QUEUED)
      @id = id
      @source = Pathname.new(source)
      @status = status
      @created_at = Time.now
      @started_at = nil
      @finished_at = nil
      @error = nil
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
      @started_at = Time.now
      self
    end

    def finish!
      @status = Status::DONE
      @finished_at = Time.now
      self
    end

    def fail!(message)
      @status = Status::FAILED
      @error = message
      @finished_at = Time.now
      self
    end
  end
end
