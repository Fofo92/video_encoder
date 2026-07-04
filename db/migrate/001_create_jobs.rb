# frozen_string_literal: true

require 'sequel'

DB.create_table?(:jobs) do
  primary_key :id
  String :job_id, unique: true, null: false

  String :source
  String :status

  DateTime :created_at
  DateTime :started_at
  DateTime :finished_at

  String :error
end
