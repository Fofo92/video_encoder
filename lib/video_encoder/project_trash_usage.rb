# frozen_string_literal: true

module VideoEncoder
  # Protects queue references, including captures read by another active project.
  class ProjectTrashUsage
    def initialize(database)
      @database = database
    end

    def validate(entry)
      paths = (entry.entries.keys + entry.entries.values).map { |path| canonical(path) }
      @database[:jobs].where(status: %w[running queued deferred]).each do |row|
        used = [row[:project_path], row[:output_path]] + sources(row[:project_path])
        used = used.compact.map { |path| canonical(path) }
        raise ProjectTrashError, 'Une tâche active utilise ces fichiers.' if used.intersect?(paths)
      end
    end

    private

    def canonical(path)
      File.realpath(path)
    rescue Errno::ENOENT, Errno::ENOTDIR
      File.expand_path(path)
    end

    def sources(path)
      return [] unless path && File.file?(path)

      if File.size(path) > 2 * 1024 * 1024
        raise ProjectTrashError,
              'Un projet actif est trop volumineux pour être vérifié.'
      end

      document_sources(JSON.parse(File.read(path)))
    rescue JSON::ParserError, KeyError, TypeError
      raise ProjectTrashError, 'Un projet actif est illisible : impossible de vérifier ses sources.'
    end

    def document_sources(document)
      raise ProjectTrashError, 'Projet actif non reconnu.' unless document.is_a?(Hash)

      entries = document['version'] == 1 ? document.fetch('timeline') : document.fetch('sources')
      raise ProjectTrashError, 'Sources du projet actif invalides.' unless entries.is_a?(Array)

      key = document['version'] == 1 ? 'source' : 'path'
      entries.filter_map { |item| item[key] if item.is_a?(Hash) && item[key].is_a?(String) }
    end
  end
end
