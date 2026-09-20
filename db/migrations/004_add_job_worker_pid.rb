# frozen_string_literal: true

Sequel.migration do
  up do
    alter_table(:jobs) do
      add_column :worker_pid, Integer
    end
  end

  down do
    alter_table(:jobs) do
      drop_column :worker_pid
    end
  end
end
