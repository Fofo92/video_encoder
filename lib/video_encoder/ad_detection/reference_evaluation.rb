# frozen_string_literal: true

module VideoEncoder
  module AdDetection
    # Known boundaries evaluate results; they never influence detection settings.
    class ReferenceEvaluation
      def initialize(reference:, source:, cut_list:, tolerance: 25)
        @reference = reference
        @source = source
        @cut_list = cut_list
        @tolerance = tolerance
      end

      def call
        validate
        used = []
        results = @reference.fetch('excluded_intervals').map { |interval| compare(interval, used) }
        { coverage: 'known_intervals_only', tolerance_frames: @tolerance,
          known_intervals: results.size, matched_known_intervals: results.count { |row| row[:within_tolerance] },
          proposed_intervals: @cut_list.intervals.size, intervals: results,
          note: 'Other proposals are unlabelled, not automatically false positives.' }
      end

      private

      def validate
        validate_identity
        @reference.fetch('excluded_intervals').each { |interval| validate_interval(*interval) }
      end

      def validate_identity
        unless @reference['format'] == 'video_encoder.ad_reference' && @reference['version'] == 1 &&
               @reference['coverage'] == 'known_intervals_only' &&
               File.expand_path(@reference.fetch('source')) == @source &&
               (Rational(@reference.fetch('frame_rate')) - @cut_list.frame_rate).abs <= Rational(1, 100)
          raise ArgumentError, 'Reference source, frame rate or coverage does not match'
        end
      end

      def validate_interval(first, last)
        return if first.is_a?(Integer) && last.is_a?(Integer) &&
                  first.between?(0, last) && last < @cut_list.frame_count

        raise ArgumentError, 'Reference interval is outside the scanned source'
      end

      def compare(expected, used)
        available = @cut_list.intervals.each_index.reject { |index| used.include?(index) }
        index = available.min_by do |candidate|
          expected.zip(@cut_list.intervals[candidate]).map { |a, b| (a - b).abs }.max
        end
        return { expected: expected, proposed: nil, within_tolerance: false } unless index

        used << index
        proposed = @cut_list.intervals[index]
        differences = proposed.zip(expected).map { |a, b| a - b }
        { expected: expected, proposed: proposed, error_frames: differences,
          within_tolerance: differences.all? { |error| error.abs <= @tolerance } }
      end
    end
  end
end
