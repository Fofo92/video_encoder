# frozen_string_literal: true

module VideoEncoder
  class CLI
    # Prints the application configuration.
    class ConfigCommand
      def initialize(config:)
        @config = config
      end

      def run
        print_database
        print_directories
        print_ffmpeg
      end

      private

      attr_reader :config

      def print_database
        puts "Database: #{config.database}"
        puts "Encoder:  #{config.encoder}"
        puts
      end

      def print_directories
        puts 'Directories'
        puts '-----------'
        puts "Incoming: #{config.directories.incoming}"
        puts "Queue:    #{config.directories.queue}"
        puts "Encoded:  #{config.directories.encoded}"
        puts "Archive:  #{config.directories.archive}"
        puts "Quarantine: #{config.directories.quarantine}"
        puts
      end

      def print_ffmpeg
        puts 'FFmpeg'
        puts '-------'
        puts "Container:   #{config.ffmpeg.container}"
        puts "Video codec: #{config.ffmpeg.video_codec}"
        puts "Preset:      #{config.ffmpeg.preset}"
        puts "Tune:        #{config.ffmpeg.tune}"
        puts "RC:          #{config.ffmpeg.rc}"
        puts "CQ:          #{config.ffmpeg.cq}"
        puts "Audio codec: #{config.ffmpeg.audio_codec}"
      end
    end
  end
end
