# frozen_string_literal: true

module VideoEncoder
  # Calculates the best time offset between two audio streams by comparing
  # overlapping samples and finding the shift with the highest correlation.
  class AudioTimelineCorrelator
    # Raised when no valid audio correlation can be computed for the given
    # source and rendered audio.
    class CorrelationUnavailable < StandardError; end

    def initialize(
      interval_seconds:,
      maximum_shift_seconds:
    )
      @interval_seconds = interval_seconds
      @maximum_shift_seconds = maximum_shift_seconds
    end

    def call(source:, rendered:)
      best_result = correlations(
        source,
        rendered
      ).max_by { |_shift, confidence| confidence }

      if best_result.nil?
        raise CorrelationUnavailable,
              'audio correlation is unavailable'
      end

      best_shift, best_confidence = best_result

      {
        offset_seconds: best_shift * interval_seconds,
        confidence: best_confidence
      }
    end

    private

    attr_reader :interval_seconds,
                :maximum_shift_seconds

    def correlations(source, rendered)
      maximum_shift = (
        maximum_shift_seconds / interval_seconds
      ).round

      (-maximum_shift..maximum_shift).filter_map do |shift|
        left, right = overlapping_samples(
          source,
          rendered,
          shift
        )

        confidence = correlation(left, right)
        next if confidence.nil?

        [shift, confidence]
      end
    end

    def overlapping_samples(source, rendered, shift)
      if shift.negative?
        left = source.drop(-shift)
        right = rendered.first(left.length)
      else
        right = rendered.drop(shift)
        left = source.first(right.length)
      end

      length = [left.length, right.length].min

      [
        left.first(length),
        right.first(length)
      ]
    end

    def correlation(left, right)
      return if left.length < 2

      left_mean = mean(left)
      right_mean = mean(right)

      left_differences = left.map do |value|
        value - left_mean
      end

      right_differences = right.map do |value|
        value - right_mean
      end

      denominator = Math.sqrt(
        squared_sum(left_differences) *
        squared_sum(right_differences)
      )

      return if denominator.zero?

      numerator = left_differences
                  .zip(right_differences)
                  .sum do |left_value, right_value|
                    left_value * right_value
                  end

      numerator / denominator
    end

    def mean(values)
      values.sum.fdiv(values.length)
    end

    def squared_sum(values)
      values.sum { |value| value**2 }
    end
  end
end
