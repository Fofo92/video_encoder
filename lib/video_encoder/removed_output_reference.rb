# frozen_string_literal: true

require 'json'

module VideoEncoder
  # A retained receipt can locate a missing historical output without reserving its old name.
  class RemovedOutputReference
    SUFFIX = '.video_encoder-export.json'

    def call(data, paths, directory)
      receipt = data["#{paths.last}#{SUFFIX}"]
      return unless receipt_file?(receipt, directory)
      return unless matching_receipt?(receipt, paths)

      target = data[paths.last] || receipt.delete_suffix(SUFFIX)
      target if missing_target?(target, directory)
    end

    private

    def receipt_file?(path, directory)
      path.is_a?(String) && File.dirname(File.expand_path(path)) == directory &&
        File.file?(path) && !File.symlink?(path) && File.size(path) <= 2 * 1024 * 1024
    end

    def matching_receipt?(path, paths)
      receipt = JSON.parse(File.read(path))
      expected = { 'format' => 'video_encoder.completed_export', 'version' => 1,
                   'project_path' => paths.first, 'output_path' => paths.last }
      receipt.is_a?(Hash) && receipt.slice(*expected.keys) == expected
    rescue JSON::ParserError, SystemCallError
      false
    end

    def missing_target?(path, directory)
      path.is_a?(String) && File.dirname(File.expand_path(path)) == directory &&
        !File.exist?(path) && !File.symlink?(path)
    end
  end
end
