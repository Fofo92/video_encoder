# frozen_string_literal: true

require_relative 'project_trash'

module VideoEncoder
  # Reuse validated, registered recovery entries; never recursively remove a directory.
  class ProjectTrashRetention
    RETENTION = 30 * 24 * 60 * 60

    def initialize(database, clock: -> { Time.now.utc })
      @database = database
      @trash = ProjectTrash.new(database)
      @clock = clock
    end

    def list
      snapshot = @trash.list
      { format: 'video_encoder.project_trash_retention', version: 1, retention_days: 30,
        entries: snapshot[:entries].map { |item| summary(item) }, errors: snapshot[:errors], deleted: [] }
    end

    def sweep(apply: false)
      result = list
      return result unless apply

      result[:entries].each { |item| purge(item, result) if item[:state] == 'due' }
      result[:entries].reject! { |item| result[:deleted].include?(item[:directory]) }
      result
    end

    private

    def summary(item)
      deadline = Time.iso8601(item.fetch(:created_at)) + RETENTION
      result = item.merge(delete_after: deadline.utc.iso8601(6))
      ProjectTrashUsage.new(@database).validate(ProjectTrashEntry.new(item.fetch(:directory)))
      result.merge(state: deadline <= @clock.call ? 'due' : 'scheduled', reason: '')
    rescue StandardError => e
      (result || item).merge(state: 'blocked', reason: e.message)
    end

    def purge(item, result)
      removed = @database.transaction(mode: :immediate) do
        entry = ProjectTrashEntry.new(item.fetch(:directory))
        next false if entry.created_at + RETENTION > @clock.call

        @trash.change('purge', item.fetch(:directory), item.fetch(:token))
        true
      end
      result[:deleted] << item.fetch(:directory) if removed
    rescue StandardError => e
      item.merge!(state: 'blocked', reason: e.message)
      result[:errors] << "#{item[:directory]} : #{e.message}"
    end
  end
end
