# frozen_string_literal: true

module VideoEncoder
  module AdDetection
    # Builds an editable draft only. Does not enqueue or encode it.
    class ComskipProject
      attr_reader :ignored_boundary_intervals

      def initialize(source:, cut_list:, first: 0, last: nil, lock_outer_bounds: false)
        raise ArgumentError, 'Locked outer bounds require an explicit OUT' if lock_outer_bounds && last.nil?

        @source = source
        @cut_list = cut_list
        @first = first
        @last = last || (cut_list.frame_count - 1)
        @lock_outer_bounds = lock_outer_bounds
        @ignored_boundary_intervals = []
      end

      def call
        validate_bounds

        segments = complement
        raise ArgumentError, 'No programme retained: review the raw Comskip results' if segments.empty?
        raise ArgumentError, 'Single-frame fragment requires manual review' if segments.any? { |a, b| a == b }

        { format: 'video_encoder.trim_project', version: 2,
          sources: [{ id: 'source', path: @source }],
          timeline: segments.map do |a, b|
            { type: 'segment', source_id: 'source', start_frame: a, end_frame: b }
          end }
      end

      private

      def validate_bounds
        return if @first.is_a?(Integer) && @last.is_a?(Integer) &&
                  @first.between?(0, @last - 1) && @last < @cut_list.frame_count

        raise ArgumentError, 'IN/OUT must be inside the scanned source'
      end

      def complement
        cursor = @first
        kept = []
        applicable_intervals.each do |first, last|
          next if last < @first || first > @last

          kept << [cursor, first - 1] if first > cursor
          cursor = [last + 1, @last + 1].min
        end
        kept << [cursor, @last] if cursor <= @last
        kept
      end

      def applicable_intervals
        return @cut_list.intervals unless @lock_outer_bounds

        if @cut_list.intervals.any? { |first, last| first <= @first && last >= @last }
          raise ArgumentError, 'Detector excludes the entire manual envelope: review required'
        end

        @ignored_boundary_intervals = @cut_list.intervals.select do |first, last|
          touches_boundary?(first, last)
        end
        @cut_list.intervals.select { |first, last| first > @first && last < @last }
      end

      def touches_boundary?(first, last)
        @first.between?(first, last) || @last.between?(first, last)
      end
    end
  end
end
