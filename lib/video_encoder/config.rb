# frozen_string_literal: true

require 'yaml'

module VideoEncoder
  # Configuration wrapper for VideoEncoder settings.
  class Config
    def self.load(path = 'config/video_encoder.yml')
      if File.exist?(path)
        new(YAML.load_file(path) || {})
      else
        raise "Configuration file not found: #{path}"
      end
    end

    def initialize(data)
      @data = data
    end

    def database
      @data['database']
    end

    def encoder
      @data['encoder']
    end

    def directories
      Directories.new(@data['directories'])
    end

    def ffmpeg
      FFmpegConfig.new(@data['ffmpeg'])
    end
  end
end
