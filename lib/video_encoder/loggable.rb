# frozen_string_literal: true

module VideoEncoder
  # Shared logging helpers.
  module Loggable
    private

    def log(message)
      logger.info(message)
    end
  end
end
