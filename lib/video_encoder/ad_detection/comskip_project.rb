# frozen_string_literal: true

module VideoEncoder
  module AdDetection
    # Builds an editable draft only. Does not enqueue or encode it.
    class ComskipProject
      def initialize(source:, cut_list:, first: 0, last: nil)
        @source = source
        @cut_list = cut_list
        @first = first
        @last = last || (cut_list.frame_count - 1)
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
        @cut_list.intervals.each do |first, last|
          next if last < @first || first > @last

          kept << [cursor, first - 1] if first > cursor
          cursor = [last + 1, @last + 1].min
        end
        kept << [cursor, @last] if cursor <= @last
        kept
      end
    end
  end
end
