# frozen_string_literal: true

require_relative 'quarantine_files'

module VideoEncoder
  # A completed queue job or an exact export receipt is required in addition to files.
  class QuarantineEvidence
    ACTIVE = %w[running queued deferred].freeze

    def initialize(database)
      @database = database
    end

    def associations(original, path, legacy: false)
      references = relevant_rows.filter_map do |row, sources|
        matches = matching_sources(sources, original, path, legacy)
        unless matches.empty?
          { 'project' => row[:project_path], 'output' => row[:output_path],
            'original' => matches.first }
        end
      end
      if legacy && references.map { |item| item['original'] }.uniq.size != 1
        raise QuarantinePolicyError, 'Origine absente ou ambiguë : conserver la source pour examen.'
      end

      references.uniq { |item| item.values_at('project', 'output') }
    end

    def check(original, path, saved)
      rows = project_rows
      rows.each do |row, sources|
        if ACTIVE.include?(row[:status]) && sources.any? { |source| same?(source, original, path) }
          raise QuarantinePolicyError, 'Source utilisée par une tâche active, en attente ou reportée.'
        end
      end
      projects = (saved + associations(original, path)).uniq { |item| item.values_at('project', 'output') }
      raise QuarantinePolicyError, 'Aucun projet associé vérifiable : examen nécessaire.' if projects.empty?

      projects.map { |item| validate_pair(item, original, path) }
    end

    private

    def relevant_rows
      project_rows.group_by { |row, _sources| row[:project_path] }.values.map do |attempts|
        attempts.reverse.find { |row, _sources| row[:status] == 'done' } || attempts.last
      end
    end

    def matching_sources(sources, original, path, legacy)
      return sources.select { |source| File.basename(source) == File.basename(path) } if legacy

      sources.select { |source| [original, path].include?(source) }
    end

    def project_rows
      @project_rows ||= read_project_rows
    end

    def read_project_rows
      @database[:jobs].order(:id).all.filter_map do |row|
        [row, QuarantineFiles.sources(row[:project_path])]
      rescue StandardError => e
        raise QuarantinePolicyError, "Projet actif invérifiable : #{e.message}" if ACTIVE.include?(row[:status])

        nil
      end
    end

    def same?(source, original, path)
      [original, path].include?(source) || (File.exist?(source) && File.identical?(source, path))
    end

    def validate_pair(item, original, path)
      project = item.fetch('project')
      output = item.fetch('output')
      validate_paths(project, output, path)
      raise QuarantinePolicyError, 'Le projet ne référence plus la source.' unless
        QuarantineFiles.sources(project).any? { |source| same?(source, original, path) }

      digest = Digest::SHA256.hexdigest(QuarantineFiles.bytes(project))
      if item['sha256'] && (item['sha256'] != digest || item['output_signature'] != QuarantineFiles.signature(output))
        raise QuarantinePolicyError, 'Projet ou résultat modifié depuis sa vérification : examen nécessaire.'
      end

      completed!(project, output, digest)
      item.merge('sha256' => digest, 'output_signature' => QuarantineFiles.signature(output))
    end

    def validate_paths(project, output, path)
      raise QuarantinePolicyError, 'Chemins projet/résultat non reconnus.' unless
        File.extname(project).downcase == '.json' && File.extname(output).downcase == '.mkv'

      QuarantineFiles.regular(project)
      QuarantineFiles.regular(output)
      workspace = TrimWorkspace.directory_for(output)
      if File.exist?(workspace)
        raise QuarantinePolicyError,
              'Espace de travail présent : encodage ou reprise à examiner.'
      end
      raise QuarantinePolicyError, 'Résultat encodé vide ou confondu avec la capture.' if
        File.empty?(output) || File.identical?(output, path) || File.identical?(project, path)
    end

    def completed!(project, output, digest)
      receipt_path = "#{output}.video_encoder-export.json"
      valid = if File.exist?(receipt_path) || File.symlink?(receipt_path)
                valid_receipt?(receipt_path, project, output, digest)
              else
                @database[:jobs].where(project_path: project, output_path: output, status: 'done').any?
              end
      raise QuarantinePolicyError, 'Encodage achevé non confirmé par la file ou son reçu.' unless valid
    end

    def valid_receipt?(path, project, output, digest)
      receipt = QuarantineFiles.document(path)
      expected = { 'format' => 'video_encoder.completed_export', 'version' => 1,
                   'project_path' => project, 'output_path' => output,
                   'project_sha256' => digest, 'byte_size' => File.size(output) }
      receipt.slice(*expected.keys) == expected &&
        Time.iso8601(receipt.fetch('modified_at')).utc.iso8601(6) == File.mtime(output).utc.iso8601(6)
    end
  end
end
