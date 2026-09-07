# frozen_string_literal: true

require 'pathname'

module VideoEncoder
  # Finds active trim exports that still depend on a source.
  class ActiveTrimExportSourceUsage
    def initialize(
      repo:,
      reader: File,
      source_paths: TrimProjectSourcePaths.new
    )
      @repo = repo
      @reader = reader
      @source_paths = source_paths
    end

    def call(source_path)
      target = normalize(source_path)

      repo.all.select do |job|
        active_trim_export?(job) &&
          project_uses?(job, target)
      end
    end

    private

    attr_reader :repo, :reader, :source_paths

    def active_trim_export?(job)
      job.kind == TrimExportJob::KIND &&
        (job.queued? || job.running?)
    end

    def project_uses?(job, target)
      json = reader.read(job.project_path)

      source_paths.call(json).any? do |path|
        normalize(path) == target
      end
    end

    def normalize(path)
      Pathname(path).expand_path.cleanpath
    end
  end
end
