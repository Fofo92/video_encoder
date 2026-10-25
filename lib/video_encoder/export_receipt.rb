# frozen_string_literal: true

require 'digest'
require 'json'
require 'open3'
require 'tempfile'
require 'time'

module VideoEncoder
  # Records the final output only after a completed project export.
  class ExportReceipt
    def call(project_path:, project_json:, trim_project:, output_path:, timings: nil)
      path = File.expand_path(output_path.to_s)
      before = File.stat(path)
      details = probe(path)
      after = File.stat(path)
      raise 'Output changed during inspection' unless signature(before) == signature(after)

      document = {
        format: 'video_encoder.completed_export', version: 1,
        completed_at: Time.now.utc.iso8601(6),
        project_path: File.expand_path(project_path.to_s),
        project_sha256: Digest::SHA256.hexdigest(project_json),
        output_path: path, byte_size: after.size, modified_at: after.mtime.utc.iso8601(6),
        roles: roles(trim_project), probe: details
      }
      document[:timings] = timings if timings
      document.merge!(project_binding(project_json))
      write(path, document)
    rescue StandardError => e
      warn "Export completed; vidb receipt unavailable: #{e.message}"
      nil
    end

    private

    def project_binding(project_json)
      project = JSON.parse(project_json)
      metadata = project.slice('project_id', 'vidb')
      metadata['vidb'] = metadata['vidb'].slice('record_id', 'binding_token') if metadata['vidb'].is_a?(Hash)
      metadata
    end

    def probe(path)
      out, error, status = Open3.capture3('ffprobe', '-v', 'error', '-show_streams', '-show_format',
                                          '-of', 'json', path)
      raise error unless status.success?

      JSON.parse(out)
    end

    def signature(stat)
      [stat.size, stat.mtime, stat.ino]
    end

    def roles(project)
      sources = project.segments.map(&:source).uniq
      tracks = TrackSelector.new.select_audio_outputs(sources)
      tracks.select { |track| track.complete_for?(sources) }.map { |track| track.role.to_s }
    end

    def write(path, document)
      destination = "#{path}.video_encoder-export.json"
      Tempfile.create(['.video-encoder-export-', '.json'], File.dirname(path)) do |file|
        file.write(JSON.pretty_generate(document))
        file.flush
        file.fsync
        File.chmod(0o644, file.path)
        File.rename(file.path, destination)
      end
      destination
    end
  end
end
