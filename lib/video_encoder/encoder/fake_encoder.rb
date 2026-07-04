# frozen_string_literal: true

module VideoEncoder
  module Encoder
    # A fake encoder used for testing and simulation purposes.
    class FakeEncoder < Base
      def initialize(logger: $stdout)
        @logger = logger
      end

      def encode(job)
        raise 'Simulated encoder failure' if job.source.to_s.include?('fail')

        3.times do |i|
          @logger.puts("[FakeEncoder] #{job.source} #{i + 1}/3")
          sleep 1
        end
      end
    end
  end
end
