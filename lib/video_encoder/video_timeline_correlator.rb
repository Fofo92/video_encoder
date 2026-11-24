# frozen_string_literal: true

module VideoEncoder
  # Measures temporal alignment between two video frame sequences.
  class VideoTimelineCorrelator
    def initialize(
      frame_rate:,
      maximum_shift_seconds:,
      boundary_retry: nil
    )
      @frame_rate = frame_rate
      @maximum_shift_seconds = maximum_shift_seconds
      @boundary_retry = boundary_retry
    end

    def call(source:, rendered:)
      maximum_shift = shift_in_frames(maximum_shift_seconds)
      best = best_correlation(source, rendered, maximum_shift)
      if retry_at_boundary?(best, maximum_shift)
        retry_shift = shift_in_frames(boundary_retry.fetch(:maximum_shift_seconds))
        best = best_correlation(source, rendered, retry_shift)
      end
      best_shift, best_confidence = best

      {
        offset_seconds: best_shift.fdiv(frame_rate),
        confidence: best_confidence
      }
    end

    private

    attr_reader :frame_rate,
                :maximum_shift_seconds,
                :boundary_retry

    def shift_in_frames(seconds)
      (seconds * frame_rate).round
    end

    def retry_at_boundary?(best, maximum_shift)
      return false unless boundary_retry && best

      shift, confidence = best
      shift.abs == maximum_shift && confidence < boundary_retry.fetch(:minimum_confidence)
    end

    def best_correlation(source, rendered, maximum_shift)
      correlations(source, rendered, maximum_shift).max_by(&:last)
    end

    def correlations(source, rendered, maximum_shift)
      (-maximum_shift..maximum_shift).filter_map do |shift|
        left, right = overlapping_frames(
          source,
          rendered,
          shift
        )

        confidence = correlation(
          left.flatten,
          right.flatten
        )

        next if confidence.nil?

        [shift, confidence]
      end
    end

    def overlapping_frames(source, rendered, shift)
      if shift.negative?
        left = source.drop(-shift)
        right = rendered.first(left.length)
      else
        right = rendered.drop(shift)
        left = source.first(right.length)
      end

      length = [
        left.length,
        right.length
      ].min

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

      pairs = left_differences.zip(
        right_differences
      )

      numerator = pairs.sum do |left_value, right_value|
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
