# frozen_string_literal: true

require 'json'
require 'pathname'
require_relative 'project_relocation_files'

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
        validate_destinations(files, rows)
        return files.plan if preview

        files.copy
        rows.each do |row|
          @database[:jobs].where(id: row[:id]).update(
            project_path: files.project_destination,
            output_path: files.output_destination(row[:output_path])
          )
        end
      end
      files.finish
      files.project_destination
    rescue StandardError
      rollback_files(files)
      raise
    end

    private

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

    def validate_destinations(files, rows)
      own_ids = rows.map { |row| row[:id] }
      @database[:jobs].exclude(id: own_ids).each do |row|
        next unless canonical_path(row[:project_path]) == files.project_destination ||
                    files.destinations.include?(canonical_path(row[:output_path])) ||
                    files.sources.include?(canonical_path(row[:output_path]))

        raise ProjectRelocationError, 'La destination est déjà référencée par une autre tâche.'
      end
    end
  end
end
