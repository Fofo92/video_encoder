# frozen_string_literal: true

require_relative 'comskip_evidence'
require_relative 'comskip_reprise_advice'

module VideoEncoder
  module AdDetection
    # Creates an opt-in alternative, never replaces the raw or locked proposal.
    class ComskipRepriseExperiment
      def initialize(source:, workspace:, cuts:, first:, last:)
        @source = source
        @workspace = workspace
        @cuts = cuts
        @first = first
        @last = last
      end

      def call
        evidence = ComskipEvidence.new(File.read("#{@workspace}/analysis.log"), source: @source,
                                                                                rate: @cuts.frame_rate)
        suggestions = ComskipRepriseAdvice.new(evidence: evidence, cut_list: @cuts, first: @first, last: @last).call
        refined = refined_cuts(suggestions)
        report = { status: 'experimental', needs_manual_review: true, suggestions: suggestions,
                   project: nil, changed_reprises: suggestions.count { |row| row[:suggested_resume] } }
        report[:project] = write_project(refined) if report[:changed_reprises].positive?
        [report, refined]
      rescue ArgumentError, Errno::ENOENT, Errno::EEXIST => e
        [{ status: 'unavailable', reason: e.message, project: nil }, nil]
      end

      private

      def refined_cuts(suggestions)
        changes = suggestions.to_h { |row| [row[:current_resume] - 1, row[:suggested_resume]] }
        rows = @cuts.intervals.map { |first, last| "#{first + 1} #{changes[last] || (last + 1)}" }
        header = "FILE PROCESSING COMPLETE #{@cuts.frame_count} FRAMES AT #{(@cuts.frame_rate * 100).to_i}"
        ComskipCutList.new(([header, '-----'] + rows).join("\n"))
      end

      def write_project(refined)
        project = ComskipProject.new(source: @source, cut_list: refined, first: @first, last: @last,
                                     lock_outer_bounds: true).call
        path = "#{@workspace}/proposal-experimental-reprises-#{@first}-#{@last}.json"
        bytes = "#{JSON.pretty_generate(project)}\n"
        unless File.file?(path) && File.binread(path) == bytes
          File.open(path, File::WRONLY | File::CREAT | File::EXCL) { |file| file.write(bytes) }
        end
        path
      end
    end
  end
end
