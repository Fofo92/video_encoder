# frozen_string_literal: true

module VideoEncoder
  module AdDetection
    # Experimental: suggest only a unique strong transition just before a stable
    # logo return. Human references are deliberately not accepted as input.
    class ComskipRepriseAdvice
      def initialize(evidence:, cut_list:, first:, last:)
        @evidence = evidence
        @cuts = cut_list
        @first = first
        @last = last
        @rate = cut_list.frame_rate
      end

      def call
        @cuts.intervals.each_with_index.filter_map do |(first, last), index|
          next unless first > @first && last < @last

          current = last + 1
          ceiling = [@last, @cuts.intervals[index + 1]&.first || @last].min
          advise(current, ceiling)
        end
      end

      private

      def advise(current, ceiling)
        row = { current_resume: current, suggested_resume: nil, needs_manual_review: true }
        logos = @evidence.logos.select do |logo|
          logo[:first] > current && logo[:first] <= [current + (30 * @rate), ceiling - 1].min &&
            logo[:duration_frames] >= 60 * @rate
        end
        return row.merge(reason: 'No unique stable logo return within 30 seconds') unless logos.one?

        logo = logos.first
        scenes = nearby_scenes(current, logo[:first], ceiling)
        return row.merge(reason: 'No unique strong transition before logo return') unless scenes.one?

        scene = scenes.first
        row.merge(suggested_resume: scene[:frame], shift_frames: scene[:frame] - current,
                  scene_timestamp_seconds: scene[:seconds], scene_strength: scene[:strength],
                  logo_return_log_frame: logo[:first],
                  reason: 'Unique strong transition within 8 seconds before a stable logo return')
      end

      def nearby_scenes(current, logo_return, ceiling)
        @evidence.scenes.select do |scene|
          scene[:strength] >= 90 && scene[:frame] > current && scene[:frame] < ceiling &&
            scene[:frame] <= logo_return && scene[:frame] >= logo_return - (8 * @rate)
        end
      end
    end
  end
end
