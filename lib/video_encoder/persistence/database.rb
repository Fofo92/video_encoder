# frozen_string_literal: true

require 'sequel'

Sequel.extension :migration

module VideoEncoder
  module Persistence
    # Opens the database and applies pending schema migrations.
    class Database
      MIGRATIONS_PATH = File.expand_path(
        '../../../db/migrations',
        __dir__
      ).freeze

      def self.connect(path = 'video_encoder.db')
        database = Sequel.sqlite(path)

        Sequel::Migrator.run(database, MIGRATIONS_PATH)

        database
      end
    end
  end
end
