# frozen_string_literal: true

Sequel.migration do
  up do
    alter_table(:jobs) do
      add_column(
        :kind,
        String,
        null: false,
        default: 'encoding'
      )
      add_column :project_path, String
      add_column :output_path, String

      add_index %i[kind status]
    end
  end

  down do
    alter_table(:jobs) do
      drop_index %i[kind status]

      drop_column :output_path
      drop_column :project_path
      drop_column :kind
    end
  end
end
