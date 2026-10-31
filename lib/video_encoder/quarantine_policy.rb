# frozen_string_literal: true

require_relative 'quarantine_ledger'
require_relative 'quarantine_evidence'

module VideoEncoder
  # Preview is read-only; each actual deletion rechecks evidence under the queue lock.
  class QuarantinePolicy
    def initialize(database:, root:, clock: -> { Time.now.utc })
      @ledger = QuarantineLedger.new(database: database, root: root, clock: clock)
      @evidence = QuarantineEvidence.new(database)
      @clock = clock
    end

    def list
      @evidence = QuarantineEvidence.new(@ledger.database)
      errors = []
      entries = @ledger.entries.map { |entry| summary(entry) }
      known = entries.map { |entry| entry[:path] }
      untracked_paths(known).each do |path|
        entries << { path: path, entered_at: nil, delete_after: nil, state: 'untracked',
                     reason: legacy_reason(path), projects: [] }
      end
      response(entries, errors)
    rescue SystemCallError => e
      response(entries || [], [e.message])
    end

    def enroll(path, project: nil)
      enroll_entry(path, project: project)
      list
    end

    def sweep(apply: false)
      return list unless apply

      enroll_legacy
      deleted = []
      errors = []
      @ledger.entries.each do |entry|
        next if Time.iso8601(entry[:delete_after]) > @clock.call

        delete_due(entry, deleted)
      rescue StandardError => e
        errors << "#{entry[:path]} : #{e.message}"
      end
      result = list
      result[:deleted] = deleted
      result[:errors].concat(errors)
      result
    end

    private

    def enroll_entry(path, project: nil)
      @ledger.synchronize do
        @evidence = QuarantineEvidence.new(@ledger.database)
        original, checked = legacy_candidate(path, project)
        @ledger.record(original, path, projects: checked)
      end
    end

    def enroll_legacy
      known = @ledger.entries.map { |entry| entry[:path] }
      untracked_paths(known).each do |path|
        enroll_entry(path)
      rescue StandardError
        # No deletion or deadline is allowed for an unverified legacy source.
        next
      end
    end

    def delete_due(entry, deleted)
      @ledger.synchronize do
        @evidence = QuarantineEvidence.new(@ledger.database)
        fresh = @ledger.current(entry[:path])
        next unless fresh && fresh[:id] == entry[:id]

        item = summary(fresh)
        next unless item[:state] == 'due'

        @ledger.remember(fresh, item[:projects])
        # A second exact identity check after metadata inspection protects replacements.
        verify_source(fresh)
        File.unlink(fresh[:path])
        @ledger.deleted(fresh)
        deleted << fresh[:path]
      end
    end

    def legacy_reason(path)
      legacy_candidate(path, nil)
      'Preuves disponibles : le prochain contrôle automatique démarrera un délai neuf de 30 jours.'
    rescue StandardError => e
      "Examen nécessaire, suivi non activé : #{e.message}"
    end

    def legacy_candidate(path, project)
      path = @ledger.validate_path(path)
      validate_source_type(path)
      projects = project ? project_reference(project, path) : @evidence.associations(nil, path, legacy: true)
      original = projects.first.fetch('original')
      if File.exist?(original) || File.symlink?(original)
        raise QuarantinePolicyError, 'Emplacement initial encore présent ou origine inconnue.'
      end

      [original, @evidence.check(original, path, projects)]
    end

    def untracked_paths(known)
      Dir.children(@ledger.root).sort.filter_map do |name|
        path = File.join(@ledger.root, name)
        path unless known.include?(path) || name.start_with?('.') || File.directory?(path)
      end
    end

    def project_reference(project, path)
      project = File.expand_path(project)
      sources = QuarantineFiles.sources(project).select { |source| File.basename(source) == File.basename(path) }
      raise QuarantinePolicyError, 'Le projet ne désigne pas une origine unique pour cette capture.' unless sources.one?

      [{ 'project' => project, 'output' => project.sub(/\.json\z/i, '.mkv'), 'original' => sources.first }]
    end

    def response(entries, errors)
      { format: 'video_encoder.quarantine', version: 1, retention_days: 30, entries: entries,
        errors: errors, deleted: [] }
    end

    def summary(entry)
      item = entry.slice(:id, :path, :original, :entered_at, :delete_after)
      verify_source(entry)
      projects = @evidence.check(entry[:original], entry[:path], JSON.parse(entry[:projects]))
      due = Time.iso8601(entry[:delete_after]) <= @clock.call
      item.merge(state: due ? 'due' : 'scheduled', reason: '', projects: projects)
    rescue StandardError => e
      item.merge(state: 'blocked', reason: e.message, projects: [])
    end

    def verify_source(entry)
      path = @ledger.validate_path(entry[:path])
      validate_source_type(path)
      raise QuarantinePolicyError, 'Source remplacée ou modifiée : suppression suspendue.' unless
        JSON.parse(entry[:signature]) == QuarantineFiles.signature(path)
      raise QuarantinePolicyError, 'La source est encore présente à son emplacement initial.' if
        File.exist?(entry[:original]) || File.symlink?(entry[:original])
    end

    def validate_source_type(path)
      raise QuarantinePolicyError, 'Type de capture non reconnu : examen nécessaire.' unless
        %w[.m2t .ts .mts .m2ts].include?(File.extname(path).downcase)
    end
  end
end
