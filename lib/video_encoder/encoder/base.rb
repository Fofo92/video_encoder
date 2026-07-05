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
    end
  end
end
