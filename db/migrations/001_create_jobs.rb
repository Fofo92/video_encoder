# frozen_string_literal: true

Sequel.migration do
  up do
    create_table?(:jobs) do
      primary_key :id
      String :job_id, null: false, unique: true
      String :source
      String :status
      DateTime :created_at
      DateTime :started_at
      DateTime :finished_at
      String :error
      Integer :attempts, default: 0
    end
  end

  down do
    drop_table?(:jobs)
  end
end
