# frozen_string_literal: true

module VideoEncoder
  # Calculates subtitle timing corrections from alignment results.
  class SubtitleSynchronizationCorrection
    class AlignmentUnavailable < StandardError; end

    def initialize(minimum_confidence: 0.95)
      @minimum_confidence = minimum_confidence
    end

    def call(
      rendered_alignment:,
      transport_alignment:
    )
      confidence = [
        rendered_alignment.fetch(:confidence),
        transport_alignment.fetch(:confidence)
      ].min

      if confidence < minimum_confidence
        raise AlignmentUnavailable,
              'subtitle alignment confidence is too low'
      end

      {
        offset_seconds: (
          rendered_alignment.fetch(:offset_seconds) -
          transport_alignment.fetch(:offset_seconds)
        ),
        confidence: confidence
      }
    end

    private

    attr_reader :minimum_confidence
  end
end
