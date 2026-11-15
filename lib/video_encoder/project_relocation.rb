# frozen_string_literal: true

require 'json'
require 'pathname'
require_relative 'project_relocation_files'
require_relative 'removed_project_reference'

module VideoEncoder
  # Moves the project and its outputs while an immediate SQLite transaction
  # prevents a worker from claiming any affected queued job.
  class ProjectRelocation
    def initialize(database)
      @database = database
    end

    def call(project_path, directory, name: nil, preview: false)
      files = nil
      @database.transaction(mode: :immediate) do
        raise ProjectRelocationError, 'Les liens symboliques ne sont pas déplaçables.' if File.symlink?(project_path)

        project = File.realpath(project_path)
        rows = @database[:jobs].all.select { |row| same_path?(row[:project_path], project) }
        raise ProjectRelocationError, 'Un encodage utilise ce projet.' if rows.any? { |row| row[:status] == 'running' }

        files = ProjectRelocationFiles.new(project, directory, rows, name: name)
        files.prepare
        retired = validate_destinations(files, rows)
        return files.plan if preview

        files.copy
        update_job_paths(files, rows, retired)
      end
      files.finish
      files.project_destination
    rescue StandardError
      rollback_files(files)
      raise
    end

    private

    def update_job_paths(files, rows, retired)
      retired.each { |id, reference| @database[:jobs].where(id: id).update(reference) }
      rows.each do |row|
        @database[:jobs].where(id: row[:id]).update(
          project_path: files.project_destination,
          output_path: files.output_destination(row[:output_path])
        )
      end
    end

    def rollback_files(files)
      return if files.nil? || files.committed?

      files.rollback
    end

    def same_path?(left, right)
      return false if left.nil?

      File.realpath(left) == right
    rescue Errno::ENOENT
      File.expand_path(left) == right
    end

    def canonical_path(path)
      return if path.nil?

      expanded = File.expand_path(path)
      File.join(File.realpath(File.dirname(expanded)), File.basename(expanded))
    rescue Errno::ENOENT
      expanded
    end

    def destination_conflict?(files, row)
      canonical_path(row[:project_path]) == files.project_destination ||
        files.destinations.include?(canonical_path(row[:output_path])) ||
        files.sources.include?(canonical_path(row[:output_path]))
    end

    def validate_destinations(files, rows)
      own_ids = rows.map { |row| row[:id] }
      @database[:jobs].exclude(id: own_ids).filter_map do |row|
        next unless destination_conflict?(files, row)

        reference = RemovedProjectReference.new.call(row)
        raise ProjectRelocationError, 'La destination est déjà référencée par une autre tâche.' unless reference

        [row[:id], reference]
      end
    end
  end
end
