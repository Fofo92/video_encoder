# frozen_string_literal: true

require 'json'

module VideoEncoder
  # Serializes audio preflight results for external consumers.
  class AudioPreflightReport
    def call(results)
      JSON.generate(
        version: 1,
        audio_checks: results.map { |result| serialize_result(result) }
      )
    end

    private

    def serialize_result(result)
      track = result.fetch(:track)
      frame_rate = result.fetch(:frame_rate)

      {
        source: result.fetch(:source).path.to_s,
        track_index: track.index,
        language: track.language,
        start_frame: result.fetch(:start_frame),
        end_frame: result.fetch(:end_frame),
        frame_rate: {
          numerator: frame_rate.numerator,
          denominator: frame_rate.denominator
        },
        analysis: serialize_analysis(result.fetch(:analysis))
      }
    end

    def serialize_analysis(analysis)
      {
        status: analysis.fetch(:status).to_s,
        sample_count: analysis.fetch(:sample_count),
        mean_volume_db: serialize_volume(analysis.fetch(:mean_volume_db)),
        max_volume_db: serialize_volume(analysis.fetch(:max_volume_db))
      }
    end

    def serialize_volume(value)
      value == -Float::INFINITY ? '-inf' : value
    end
  end
end
