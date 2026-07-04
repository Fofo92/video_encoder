# frozen_string_literal: true

module VideoEncoder
  module Encoder
    # Base encoder interface for video encoding jobs.
    # Implementations must define the #encode method.
    class Base
      def encode(_job)
        raise NotImplementedError
      end
    end
  end
end
