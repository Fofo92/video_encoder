# frozen_string_literal: true

module VideoEncoder
  module Encoder
    # Base encoder interface for video encoding jobs.
    # Implementations must define the #encode method.
    class Base
      attr_reader :logger

      def initialize(logger:)
        @logger = logger
      end

      def encode(_job)
        raise NotImplementedError, "#{self.class} must implement #encode"
      end

      private

      def log(message)
        logger.info(message)
      end
    end
  end
end
