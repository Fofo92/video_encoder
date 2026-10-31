# frozen_string_literal: true

require_relative 'quarantine_files'
require_relative 'quarantine_evidence'

module VideoEncoder
  # Lives in the queue database: recording and purging share its writer lock.
  class QuarantineLedger
    RETENTION = 30 * 24 * 60 * 60

    attr_reader :database, :root

    def initialize(database:, root:, clock: -> { Time.now.utc })
      @database = database
      @root = File.expand_path(root)
      @clock = clock
      database.create_table?(:quarantine_sources) do
        primary_key :id
        String :path, null: false
        String :original, null: false
        String :entered_at, null: false
        String :delete_after, null: false
        String :signature, text: true, null: false
        String :projects, text: true, null: false
        String :deleted_at
      end
    end

    def synchronize(&)
      database.transaction(mode: :immediate, &)
    end

    def validate_path(path)
      expanded = File.expand_path(path.to_s)
      valid = File.directory?(root) && !File.symlink?(root) &&
              File.dirname(expanded) == root && QuarantineFiles.regular(expanded) == expanded
      unless valid
        raise QuarantinePolicyError,
              'La source doit être un fichier régulier directement dans la quarantaine.'
      end

      expanded
    end

    def record(original, destination, projects: [])
      path = validate_path(destination)
      raise QuarantinePolicyError, 'Cette source est déjà suivie.' if current(path)

      now = @clock.call.utc
      projects = QuarantineEvidence.new(database).associations(File.expand_path(original.to_s), path) if projects.empty?
      begin
        projects = QuarantineEvidence.new(database).check(File.expand_path(original.to_s), path, projects)
      rescue StandardError
        # Keep the known project/output pairs even if their verification is incomplete.
      end
      table.insert(path: path, original: File.expand_path(original.to_s), entered_at: now.iso8601(6),
                   delete_after: (now + RETENTION).iso8601(6),
                   signature: JSON.generate(QuarantineFiles.signature(path)), projects: JSON.generate(projects))
    end

    def current(path)
      table.where(path: path, deleted_at: nil).order(Sequel.desc(:id)).first
    end

    def entries
      table.where(deleted_at: nil).all.select { |entry| File.dirname(entry[:path]) == root }
    end

    def remember(entry, projects)
      table.where(id: entry.fetch(:id)).update(projects: JSON.generate(projects))
    end

    def deleted(entry)
      table.where(id: entry.fetch(:id)).update(deleted_at: @clock.call.utc.iso8601(6))
    end

    private

    def table
      database[:quarantine_sources]
    end
  end
end
