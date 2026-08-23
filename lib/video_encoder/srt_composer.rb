# frozen_string_literal: true

module VideoEncoder
  # Combines normalized SRT segments into one subtitle stream.
  class SrtComposer
    def call(segments)
      entries = segments.flat_map do |segment|
        segment.split(/\r?\n\r?\n/)
      end

      composed = entries.each_with_index.map do |entry, index|
        entry.sub(/\A\d+\r?\n/, "#{index + 1}\n")
      end
      return '' if composed.empty?

      "#{composed.join("\n\n")}\n"
    end
  end
end
