# frozen_string_literal: true

require 'sequel'

DB = Sequel.sqlite('video_encoder.db')

# bootstrap table migrations
DB.create_table? :schema_migrations do
  primary_key :id
  Integer :version, unique: true, null: false
end

# migrations déjà appliquées
applied = DB[:schema_migrations].select_map(:version)

Dir['db/migrate/*.rb']
  .reject { |f| File.basename(f) == 'run.rb' }
  .sort
  .each do |file|
  version = File.basename(file, '.rb')
  next if applied.include?(version)

  puts "Running migration: #{version}"

  load file

  DB[:schema_migrations].insert_conflict(target: :version, update: {}) do
    { version: version }
  end

  puts "✔ done #{version}"
end
