# frozen_string_literal: true

module VideoEncoder
  module AdDetection
    # Native Comskip TXT uses one-based inclusive frame numbers.
    class ComskipCutList
      attr_reader :frame_count, :frame_rate, :intervals

      def initialize(text)
        lines = text.lines.map(&:strip).reject(&:empty?)
        header = /\AFILE PROCESSING COMPLETE\s+(\d+)\s+FRAMES AT\s+(\d+)\z/.match(lines.shift.to_s)
        raise ArgumentError, 'Comskip result is incomplete or unsupported' unless header

        @frame_count = Integer(header[1])
        @frame_rate = Rational(header[2].to_i, 100)
        raise ArgumentError, 'Comskip returned invalid media dimensions' unless frame_count > 1 && frame_rate.positive?

        @intervals = lines.grep_v(/\A-+\z/).map { |line| parse_interval(line) }
        validate_order
      end

      private

      def parse_interval(line)
        match = /\A(\d+)\s+(\d+)\z/.match(line)
        raise ArgumentError, "Unsupported Comskip row: #{line}" unless match

        first, last = match.captures.map { |value| Integer(value) - 1 }
        unless first.between?(0, last) && last < frame_count
          raise ArgumentError, 'Comskip cut is outside the scanned frames'
        end

        [first, last]
      end

      def validate_order
        intervals.each_cons(2) do |previous, following|
          raise ArgumentError, 'Comskip cuts overlap or are unsorted' if following.first <= previous.last
        end
      end
    end
  end
end
