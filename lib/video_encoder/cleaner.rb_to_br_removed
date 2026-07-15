# frozen_string_literal: true

require 'fileutils'

module VideoEncoder
  class Cleaner
    def initialize(logger:)
      @logger = logger
    end

    def clean(path)
    def clean(*paths)
      paths.each do |path|
        next unless File.exist?(path)

        FileUtils.rm(path)
        @logger.info("Removed #{path}")
        end
      end
      
      return unless File.exist?(path)

      FileUtils.rm(path)
      @logger.info("Removed #{path}")
    end
  end
end
