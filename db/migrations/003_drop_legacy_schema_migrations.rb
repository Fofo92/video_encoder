# frozen_string_literal: true

Sequel.migration do
  up do
    drop_table?(:schema_migrations)
  end

  down do
    create_table?(:schema_migrations) do
      primary_key :id
      Integer :version,
              null: false,
              unique: true
    end
  end
end
