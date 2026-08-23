# frozen_string_literal: true

module VideoEncoder
  # Converts DVB bitmap subtitles to SRT using CCExtractor OCR.
  class CcextractorOcr
    def initialize(
      runner:,
      executable: 'ccextractor',
      language: 'fra'
    )
      @runner = runner
      @executable = executable
      @language = language
    end

    def call(input_path:, output_path:)
      runner.run(
        executable,
        '--codec', 'dvbsub',
        '--streamtype', '6',
        '--ocrlang', language,
        '--ocr-line-split',
        '--out', 'srt',
        input_path.to_s,
        '-o', output_path.to_s
      )
    end

    private

    attr_reader :runner, :executable, :language
  end
end
