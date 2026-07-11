# frozen_string_literal: true

module VideoEncoder
  # Watches the incoming directory and queues new files for processing.
  class Watcher
    def initialize(incoming:, queue:, repo:)
      @incoming = incoming
      @queue = queue
      @repo = repo
      @known_sizes = {}
    end

    def scan_once
      file = Dir.glob(File.join(@incoming, '*')).first
      return unless file

      size = File.size(file)
      if @known_sizes[file] == size
        destination = File.join(@queue, File.basename(file))
        FileUtils.mv(file, destination)

        job = VideoEncoder::Job.new(source: destination)
        @repo.enqueue(job)

        @known_sizes.delete(file)
      else
        @known_sizes[file] = size
      end
    end
  end
end
