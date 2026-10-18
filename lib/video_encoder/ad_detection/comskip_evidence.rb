# frozen_string_literal: true

module VideoEncoder
  module AdDetection
    # Reads observations rather than final classifications. Log frames and TXT
    # export coordinates use different rates: scene timestamps are authoritative.
    class ComskipEvidence
      attr_reader :scenes, :logos

      def initialize(text, source:, rate:)
        validate(text, source, rate)
        @scenes = read_scenes(text, rate)
        @logos = read_logos(text, rate)
      end

      private

      def validate(text, source, rate)
        logged_source = text[/^Mpeg:\s*([^\r\n]+)/, 1]
        logged_rate = text[/^Average framerate:\s*([\d.]+)/, 1]
        return if logged_source == source && logged_rate && Rational(logged_rate) == rate

        raise ArgumentError, 'Comskip evidence source or average frame rate does not match'
      end

      def read_scenes(text, rate)
        pattern = /^Frame\s+(\d+)\s+\(([\d.]+)s\) - Black frame because large scene change of (\d+),/
        scenes = text.scan(pattern).map do |frame, seconds, strength|
          { frame: (Rational(seconds) * rate).round, log_frame: frame.to_i,
            seconds: seconds, strength: strength.to_i }
        end
        scenes.uniq { |scene| scene[:frame] }.sort_by { |scene| scene[:frame] }
      end

      def read_logos(text, rate)
        active = {}
        logos = []
        text.each_line do |line|
          start = /Start logo cblock (\d+)\s+frame (\d+)/.match(line)
          active[start[1]] = start[2].to_i if start
          finish = /End logo block (\d+)\s+frame (\d+)\s+Length - (\d+):(\d+):([\d.]+)/.match(line)
          next unless finish

          first = active.delete(finish[1])
          next unless first

          duration = (finish[3].to_i * 3600) + (finish[4].to_i * 60) + Rational(finish[5])
          logos << { first: first, last: finish[2].to_i, duration_frames: (duration * rate).floor }
        end
        logos
      end
    end
  end
end
