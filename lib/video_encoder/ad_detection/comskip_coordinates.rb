# frozen_string_literal: true

module VideoEncoder
  module AdDetection
    # Comskip can export field-rate coordinates for interlaced 25 fps video.
    module ComskipCoordinates
      module_function

      def convert(cuts, rate)
        return cuts if cuts.frame_rate == rate

        unless cuts.frame_rate == rate * 2
          raise ArgumentError, 'Comskip frame rate differs from the source: unsupported coordinate conversion'
        end

        # Keep only source frames entirely covered by an excluded interval.
        # Convert the exclusive end boundary, rather than rounding both ends.
        rows = cuts.intervals.filter_map do |first, last|
          start = Rational(first, 2).ceil
          finish = Rational(last + 1, 2).floor - 1
          "#{start + 1} #{finish + 1}" if start <= finish
        end
        header = "FILE PROCESSING COMPLETE #{cuts.frame_count / 2} FRAMES AT #{(rate * 100).to_i}"
        ComskipCutList.new(([header, '-----'] + rows).join("\n"))
      end
    end
  end
end
