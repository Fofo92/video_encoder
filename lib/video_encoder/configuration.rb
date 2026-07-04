# frozen_string_literal: true

require 'yaml'

module VideoEncoder
  # Configuration holds defaults and loaded settings for the encoder.
  class Configuration
    DEFAULTS = {
      'encoder' => 'fake',
      'database' => 'video_encoder.db',
      'output_directory' => './encoded',
      'ffmpeg' => {
        'preset' => 'medium',
        'crf' => 22
      }
    }.freeze

    attr_reader :data

    def initialize(data = {})
      @data = DEFAULTS.merge(data)
    end

    def encoder
      ENV.fetch('VIDEO_ENCODER', @data['encoder'])
    end

    def database
      ENV.fetch('VIDEO_ENCODER_DB', @data['database'])
    end

    def output_directory
      ENV.fetch('VIDEO_ENCODER_OUTPUT', @data['output_directory'])
    end

    def ffmpeg
      @data['ffmpeg']
    end

    def self.load(path = 'config.yml')
      if File.exist?(path)
        new(YAML.load_file(path) || {})
      else
        new
      end
    end
  end
end
