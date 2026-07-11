# frozen_string_literal: true

require 'sequel'

module VideoEncoder
  module Persistence
    # Database persistence adapter using Sequel and SQLite.
    class Database
      def self.connect(path = 'video_encoder.db')
        @connection ||= Sequel.sqlite(path)
      end
    end
  end
end
