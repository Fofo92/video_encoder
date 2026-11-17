# frozen_string_literal: true

require 'json'
require 'open3'

module VideoEncoder
  # A completed conversion may reclaim its input's name only through explicit archival.
  class CopyVersionReplacement
    def initialize(database)
      @database = database
    end

    def applies?(project, directory, name)
      return false unless safe_name?(name) && File.file?(project) && !File.symlink?(project)
      return false if File.size(project) > 2 * 1024 * 1024

      document = JSON.parse(File.read(project))
      return false unless document['format'] == 'video_encoder.copy_version'

      source = document.dig('version_change', 'source_path')
      source.is_a?(String) && File.expand_path(File.join(directory, "#{name}.mkv")) == source
    end

    def call(project, directory, name, preview:)
      database = @database.opts[:database]
      raise ProjectRelocationError, 'Cette opération nécessite la file SQLite persistante.' unless
        database.is_a?(String) && database != ':memory:' && File.file?(database)

      script = File.expand_path('copy_version_replacement.py', __dir__)
      output, error, status = Open3.capture3('python3', script, database, File.expand_path(project),
                                             File.realpath(directory), name, preview ? 'preview' : 'apply')
      raise ProjectRelocationError, error.strip unless status.success?

      JSON.parse(output, symbolize_names: true)
    end

    private

    def safe_name?(name)
      name.is_a?(String) && !name.empty? && name == name.strip &&
        !name.match?(%r{[/\\\x00-\x1f\x7f]}) && !%w[. ..].include?(name) &&
        !name.end_with?('.json', '.mkv', '.mp4', '.m4v')
    end
  end
end
