# frozen_string_literal: true

module VideoEncoder
  # Reads subtitle text produced by external OCR as valid UTF-8.
  class SubtitleTextReader
    def initialize(reader: File)
      @reader = reader
    end

    def read(path)
      reader
        .binread(path)
        .dup
        .force_encoding(Encoding::UTF_8)
        .scrub('')
    end

    private

    attr_reader :reader
  end
end
