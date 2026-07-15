# frozen_string_literal: true

module VideoEncoder
  # Encapsulates directory paths used by the video encoder.
  class Directories
    def initialize(data)
      @data = data
    end

    def incoming
      @data['incoming']
    end

    def queue
      @data['queue']
    end

    def encoding
      @data['encoding']
    end
    
    def encoded
      @data['encoded']
    end

    def archive
      @data['archive']
    end
  end
end
