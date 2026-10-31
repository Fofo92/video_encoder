# frozen_string_literal: true

module VideoEncoder
  class ProjectTrashError < StandardError; end

  # Remembers known trash roots in the same database as the export queue.
  class ProjectTrashRegistry
    def initialize(database)
      @database = database
      @database.create_table?(:project_trash_roots) { String :path, primary_key: true }
    end

    def add(path)
      root = File.expand_path(path)
      raise ProjectTrashError, 'Choisis un dossier .video_encoder_trash régulier.' unless
        File.basename(root) == '.video_encoder_trash' && File.directory?(root) && !File.symlink?(root)

      root = File.realpath(root)
      @database[:project_trash_roots].insert_conflict.insert(path: root)
      root
    end

    def roots
      @database[:project_trash_roots].order(:path).select_map(:path)
    end
  end
end
