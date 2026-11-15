# frozen_string_literal: true

module VideoEncoder
  # Keep the previous registration before starting a fresh retention period.
  class QuarantineReentry
    def initialize(database)
      @database = database
    end

    def replace(entry, attributes)
      original = attributes.fetch(:original)
      destination = attributes.fetch(:path)
      raise QuarantinePolicyError, 'Cette source est déjà suivie.' unless reentering?(entry, original, destination)

      history.insert(source_id: entry.fetch(:id), archived_at: attributes.fetch(:entered_at),
                     reason: 'source_reentered', entry: JSON.generate(entry))
      @database[:quarantine_sources].where(id: entry.fetch(:id), deleted_at: nil).update(attributes)
      entry.fetch(:id)
    end

    private

    def reentering?(entry, original, destination)
      entry[:original] == original && original != destination &&
        File.file?(original) && !File.symlink?(original) && File.identical?(original, destination)
    end

    def history
      @database.create_table?(:quarantine_source_history) do
        primary_key :id
        Integer :source_id, null: false
        String :archived_at, null: false
        String :reason, null: false
        String :entry, text: true, null: false
      end
      @database[:quarantine_source_history]
    end
  end
end
