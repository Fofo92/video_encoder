# frozen_string_literal: true

module VideoEncoder
  # Encapsulates directory paths used by the video encoder.
  class Directories
    def initialize(data)
      @data = data
    end

    def quarantine
      @data['quarantine']
    end
  end
end
