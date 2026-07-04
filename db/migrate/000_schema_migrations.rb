# frozen_string_literal: true

require 'sequel'

DB.create_table? :schema_migrations do
  String :version, primary_key: true
end
