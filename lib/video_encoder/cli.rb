# frozen_string_literal: true

module VideoEncoder
  # CLI handles command-line interface for VideoEncoder.
  class CLI
    def initialize(argv)
      @argv = argv
    end

    def run
      command = @argv.first

      case command
      when 'version'
        puts VideoEncoder::VERSION
      else
        puts usage
        exit 1
      end
    end

    private

    def usage
      <<~TEXT
        Usage:
          video_encoder version
      TEXT
    end
  end
end
