# frozen_string_literal: true

require 'sequel'

unless DB.schema(:jobs).map(&:first).include?(:attempts)
  DB.alter_table :jobs do
    add_column :attempts, Integer, default: 0
  end
end
