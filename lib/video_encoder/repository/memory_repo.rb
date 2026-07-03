# frozen_string_literal: true

module VideoEncoder
  # In-memory repository for managing job queue.
  class MemoryRepo
    def initialize
      @queue = []
    end

    def enqueue(job)
      @queue << job
    end

    def all
      @queue.dup
    end

    def next
      @queue.shift
    end

    def size
      @queue.size
    end
  end
end
