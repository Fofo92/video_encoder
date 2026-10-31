# frozen_string_literal: true

require 'time'
require_relative 'project_trash_registry'
require_relative 'project_trash_entry'
require_relative 'project_trash_usage'

module VideoEncoder
  # Lists and manages known recovery entries without recursive disk searches.
  class ProjectTrash
    def initialize(database)
      @database = database
      @registry = ProjectTrashRegistry.new(database)
    end

    def register(root)
      @registry.add(root)
    end

    def list
      errors = []
      entries = @registry.roots.flat_map { |root| list_root(root, errors) }
      { format: 'video_encoder.project_trash', version: 1, entries: entries, errors: errors }
    end

    def change(operation, directory, token)
      raise ProjectTrashError, 'Action de corbeille inconnue.' unless %w[restore purge].include?(operation)
      raise ProjectTrashError, 'Corbeille non enregistrée.' unless @registry.roots.include?(File.dirname(directory))

      @database.transaction(mode: :immediate) do
        entry = ProjectTrashEntry.new(directory)
        raise ProjectTrashError, 'Le contenu a changé : actualise la corbeille.' unless entry.token == token

        ProjectTrashUsage.new(@database).validate(entry)
        entry.public_send(operation)
      end
      directory
    end

    private

    def list_root(root, errors)
      raise ProjectTrashError, "Corbeille indisponible : #{root}" unless File.directory?(root) && !File.symlink?(root)

      Dir.children(root).sort.filter_map do |name|
        read_entry(File.join(root, name), errors)
      end
    rescue SystemCallError, ProjectTrashError => e
      errors << e.message
      []
    end

    def read_entry(path, errors)
      ProjectTrashEntry.new(path).summary
    rescue SystemCallError, ProjectTrashError, JSON::ParserError => e
      errors << "#{path} : #{e.message}"
      nil
    end
  end
end
