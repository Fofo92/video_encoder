# frozen_string_literal: true

require 'json'
require_relative 'removed_output_reference'

module VideoEncoder
  # Resolve an inactive job only from the removal manifest, never from missing files alone.
  class RemovedProjectReference
    def call(row)
      return unless %w[done failed interrupted].include?(row[:status])

      project = row[:project_path]
      output = row[:output_path]
      return unless [project, output].all? { |path| removed_path?(path) }

      paths = [project, output].map { |path| File.expand_path(path) }
      matches = manifests(paths.first).filter_map { |manifest| mapping(manifest, paths) }
      matches.first if matches.one?
    end

    private

    def removed_path?(path)
      path.is_a?(String) && !path.empty? && absent?(path)
    end

    def absent?(path)
      !File.exist?(path) && !File.symlink?(path)
    end

    def manifests(project)
      root = File.join(File.dirname(project), '.video_encoder_trash')
      return [] unless File.directory?(root) && !File.symlink?(root)

      Dir.glob(File.join(root, '*', 'manifest.json')).select do |path|
        File.file?(path) && !File.symlink?(path) && !File.symlink?(File.dirname(path))
      end
    end

    def mapping(manifest, paths)
      return if File.size(manifest) > 2 * 1024 * 1024

      data = JSON.parse(File.read(manifest))
      return unless data.is_a?(Hash)

      directory = File.dirname(manifest)
      project = data[paths.first]
      return unless recoverable?(project, directory)

      output = output_reference(data, paths, directory)
      { project_path: project, output_path: output } if output
    rescue JSON::ParserError, SystemCallError
      nil
    end

    def output_reference(data, paths, directory)
      output = data[paths.last]
      return output if recoverable?(output, directory)

      RemovedOutputReference.new.call(data, paths, directory)
    end

    def recoverable?(path, directory)
      path.is_a?(String) && File.dirname(File.expand_path(path)) == directory &&
        File.file?(path) && !File.symlink?(path)
    end
  end
end
