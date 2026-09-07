# frozen_string_literal: true

require 'pathname'

module VideoEncoder
  # Moves an eligible source into quarantine without overwriting.
  class QuarantineSource
    class UnsafeSource < StandardError; end
    class MissingDirectory < StandardError; end
    class DestinationExists < StandardError; end

    def initialize(
      check:,
      quarantine_directory:,
      file: File
    )
      @check = check
      @quarantine_directory =
        Pathname(quarantine_directory)
      @file = file
    end

    def call(source)
      result = check.call(source)

      unless result.eligible?
        reasons = result.reasons.join(', ')

        raise UnsafeSource,
              "source is not eligible: #{reasons}"
      end

      unless file.directory?(quarantine_directory)
        raise MissingDirectory,
              'quarantine directory not found: ' \
              "#{quarantine_directory}"
      end

      destination = quarantine_directory.join(
        result.source.basename
      )

      if file.exist?(destination)
        raise DestinationExists,
              'quarantine destination already exists: ' \
              "#{destination}"
      end

      create_destination_link(
        result.source,
        destination
      )
      file.unlink(result.source)

      destination
    end

    private

    attr_reader :check,
                :quarantine_directory,
                :file

    def create_destination_link(source, destination)
      file.link(source, destination)
    rescue Errno::EEXIST
      raise DestinationExists,
            'quarantine destination already exists: ' \
            "#{destination}"
    end
  end
end
