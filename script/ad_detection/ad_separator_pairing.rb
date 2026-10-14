# frozen_string_literal: true

# Conservative recovery after already paired separators. All results remain
# editable hypotheses, not confirmed advertising cuts.
module AdSeparatorPairing
  module_function

  def recover!(report)
    pairs = report.fetch('advertising_interval_hypotheses')
    return report if pairs.length < 2

    durations = pairs.map { |p| p.fetch('excluded_end_frame_inclusive') + 1 - p.fetch('excluded_start_frame') }.sort
    reference = durations.sum.fdiv(durations.length)
    return report unless durations.all? { |n| (n - reference).abs <= reference * 0.25 }

    used = pairs.flat_map { |p| [p.fetch('departure_candidate'), p.fetch('return_candidate')] }
    tail_start = pairs.map { |p| p.fetch('excluded_end_frame_inclusive') }.max
    rows = report.fetch('candidates').select { |r| r.fetch('separator_proposal', {}).fetch('start_frame', -1) > tail_start }
    eligible = rows.each_cons(2).select do |left, right|
      next false unless [left, right].all? { |r| r['status'] == 'return_hypothesis' && !used.include?(r['id']) }

      length = right.fetch('separator_proposal').fetch('end_frame_exclusive') - left.fetch('separator_proposal').fetch('start_frame')
      length.between?(60 * 25, 900 * 25) && (length - reference).abs <= reference * 0.25
    end
    # Competing interpretations must not silently choose the earliest pair.
    return report unless eligible.length == 1

    left, right = eligible.first
    first = left.fetch('separator_proposal').fetch('start_frame')
    last = right.fetch('separator_proposal').fetch('end_frame_exclusive') - 1
    left['previous_status'] = left['status']
    left['previous_boundary_frame'] = left['boundary_frame']
    left['status'] = 'departure_hypothesis'
    left['boundary_frame'] = first
    left['boundary_method'] = 'graphical onset; unique adjacent pair with duration consistent with two prior pairs'
    left.delete('boundary_sheet_frames')
    left['boundary_sheet_label'] = 'start'
    pairs << { 'status' => 'unvalidated_hypothesis', 'departure_candidate' => left.fetch('id'),
               'return_candidate' => right.fetch('id'), 'excluded_start_frame' => first,
               'excluded_end_frame_inclusive' => last, 'duration_seconds' => (last + 1 - first).fdiv(25),
               'pairing_method' => 'unique_tail_pair_with_capture_duration_evidence' }
    pairs.sort_by! { |p| p.fetch('excluded_start_frame') }
    report['pairing_revision'] = 1
    report.fetch('limitations') << 'A recovered pair uses sequence and a 25% duration tolerance from at least two prior pairs; it requires visual review and does not prove separator direction.'
    report
  end
end
