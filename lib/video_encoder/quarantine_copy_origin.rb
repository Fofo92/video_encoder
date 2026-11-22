# frozen_string_literal: true

require_relative 'quarantine_files'

module VideoEncoder
  # Proof captured in the ledger before the intermediate export is purged.
  class QuarantineCopyOrigin
    def initialize(item)
      @project = QuarantineFiles.document(item.fetch('project'))
      @proof = item.fetch('copy_origin')
    end

    def sources
      source = archived_source
      receipt = @proof.fetch('receipt')
      initial_json = @proof.fetch('project_json')
      verify_archive(source, receipt)
      verify_digest(initial_json, receipt)
      initial = JSON.parse(initial_json)
      check(initial['format'] == 'video_encoder.trim_project', 'Projet initial non reconnu.')
      QuarantineFiles.source_items(initial)
    end

    private

    def archived_source
      check(@project['format'] == 'video_encoder.copy_version' && @project['version'] == 2,
            'Projet de changement de version non reconnu.')
      source = @project.dig('version_change', 'source_path')
      paths = QuarantineFiles.version_two_sources(@project)
      check(source.is_a?(String) && source.start_with?('/') && paths == [source],
            'Source du changement de version ambiguë.')
      source
    end

    def verify_archive(source, receipt)
      output = receipt.fetch('output_path')
      manifest = @proof.fetch('manifest')
      check(manifest[output] == source && manifest["#{output}.video_encoder-export.json"] ==
            "#{source}.video_encoder-export.json", 'Manifeste de remplacement incohérent.')
      check(receipt['format'] == 'video_encoder.completed_export' && receipt['version'] == 1,
            'Reçu initial non reconnu.')
      signature = @proof.fetch('archived_signature')
      check(signature.fetch(2) == receipt.fetch('byte_size'), 'Taille du MKV initial incohérente.')
      modified = Time.at(Rational(signature.fetch(3))).utc.iso8601(6)
      check(modified == Time.iso8601(receipt.fetch('modified_at')).utc.iso8601(6),
            'Date du MKV initial incohérente.')
    end

    def verify_digest(initial_json, receipt)
      check(Digest::SHA256.hexdigest(initial_json) == receipt.fetch('project_sha256'),
            'Empreinte du projet initial incohérente.')
    end

    def check(valid, message)
      raise QuarantinePolicyError, message unless valid
    end
  end
end
