# frozen_string_literal: true

module VideoEncoder
  # Converts an editing session into a persistent trim project document.
  class ConvertTrimSession
    def initialize(loader:, serializer:)
      @loader = loader
      @serializer = serializer
    end

    def call(json)
      serializer.dump(
        loader.load(json)
      )
    end

    private

    attr_reader :loader, :serializer
  end
end
