# frozen_string_literal: true

module VideoEncoder
  # Represents an output audio track assembled from several media sources.
  class AudioOutputTrack
    SUPPORTED_ROLES = %i[french original].freeze

    attr_reader :role

    def initialize(role:, tracks_by_source:)
      raise ArgumentError, "unsupported audio role: #{role}" unless SUPPORTED_ROLES.include?(role)

      @role = role
      @tracks_by_source = tracks_by_source
    end

    def track_for(source)
      tracks_by_source.fetch(source)
    end

    def complete_for?(sources)
      sources.all? { |source| tracks_by_source.key?(source) }
    end

    private

    attr_reader :tracks_by_source
  end
end
