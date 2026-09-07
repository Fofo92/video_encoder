# frozen_string_literal: true

require 'pathname'

module VideoEncoder
  # Checks whether a source is technically safe to quarantine.
  class SourceQuarantineCheck
    Result = Struct.new(
      :source,
      :active_jobs,
      :reasons,
      keyword_init: true
    ) do
      def eligible?
        reasons.empty?
      end
    end

    def initialize(source_usage:, file: File)
      @source_usage = source_usage
      @file = file
    end

    def call(source)
      unless file.file?(source)
        return Result.new(
          source: Pathname(source),
          active_jobs: [],
          reasons: [:source_missing]
        )
      end

      active_jobs = source_usage.call(source)
      reasons = []

      reasons << :active_trim_exports unless active_jobs.empty?

      Result.new(
        source: Pathname(source),
        active_jobs: active_jobs,
        reasons: reasons
      )
    end

    private

    attr_reader :source_usage, :file
  end
end
