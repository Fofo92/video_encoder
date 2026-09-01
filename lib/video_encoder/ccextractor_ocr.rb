# frozen_string_literal: true

module VideoEncoder
  # Converts DVB bitmap subtitles to SRT using CCExtractor OCR.
  class CcextractorOcr
    # Indicates that CCExtractor completed without finding subtitles.
    class NoSubtitlesFound < StandardError; end

    # Identifies a technical CCExtractor failure eligible for fallback.
    class TechnicalFailure < StandardError
      attr_reader :failure

      def initialize(failure)
        @failure = failure
        super(failure.message)
      end
    end

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
        '--ts',
        '--analyzevideo',
        '--codec', 'dvbsub',
        '--streamtype', '6',
        '--ocrlang', language,
        '--ocr-line-split',
        '--ignoreptsjumps',
        '--out', 'srt',
        input_path.to_s,
        '-o', output_path.to_s
      )
    rescue CommandRunner::CommandFailed => e
      if e.exit_status == 10 && e.term_signal.nil?
        raise NoSubtitlesFound,
              "CCExtractor n’a trouvé aucun sous-titre dans #{input_path}"
      end

      raise TechnicalFailure.new(e), cause: e
    end

    private

    attr_reader :runner, :executable, :language
  end
end
