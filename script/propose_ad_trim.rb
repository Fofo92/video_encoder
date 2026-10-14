#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'
require 'optparse'
require 'open3'
require 'time'
require 'digest'
require 'fileutils'

# Convert experimental frame hypotheses into an editable draft, without exports.
module AdTrimProposal
  module_function

  def build(report, first: 0, last: nil)
    raise ArgumentError, 'unsupported boundary report' unless report['format'] == 'video_encoder.6ter_boundary_hypotheses' && report['version'] == 3

    count = report.fetch('decoded_frames')
    raise ArgumentError, 'invalid decoded frame count' unless count.is_a?(Integer) && count > 1

    last = count - 1 if last.nil?
    unless first.is_a?(Integer) && last.is_a?(Integer) && first >= 0 && last < count && last > first
      raise ArgumentError, 'invalid outer frame bounds'
    end
    candidates = report.fetch('candidates')
    ids = candidates.map { |candidate| candidate.fetch('id') }
    raise ArgumentError, 'duplicate candidate identifiers' unless ids.uniq == ids
    raise ArgumentError, 'unresolved candidates require review before conversion' if candidates.any? { |candidate| candidate['status'] == 'needs_review' }

    cuts = report.fetch('advertising_interval_hypotheses')
    raise ArgumentError, 'no paired advertising interval in report' if cuts.empty?

    previous_end = -1
    used_ids = []
    intervals = cuts.map do |cut|
      a = cut.fetch('excluded_start_frame')
      b = cut.fetch('excluded_end_frame_inclusive')
      unless a.is_a?(Integer) && b.is_a?(Integer) && a >= 0 && b >= a && b < count && a > previous_end
        raise ArgumentError, 'invalid, unsorted or overlapping advertising intervals'
      end
      departure = candidates.find { |candidate| candidate['id'] == cut.fetch('departure_candidate') }
      reprise = candidates.find { |candidate| candidate['id'] == cut.fetch('return_candidate') }
      unless departure && reprise && departure['status'] == 'departure_hypothesis' && reprise['status'] == 'return_hypothesis' && departure['boundary_frame'] == a && reprise['boundary_frame'] == b + 1
        raise ArgumentError, 'interval does not match its boundary candidates'
      end
      pair_ids = [departure['id'], reprise['id']]
      raise ArgumentError, 'a boundary candidate is used twice' unless (used_ids & pair_ids).empty?

      used_ids.concat(pair_ids)
      previous_end = b
      [a, b]
    end
    cursor = first
    kept = []
    intervals.each do |a, b|
      next if b < first || a > last

      a = [a, first].max
      b = [b, last].min
      kept << [cursor, a - 1] if cursor < a
      cursor = b + 1
    end
    kept << [cursor, last] if cursor <= last
    raise ArgumentError, 'no retained images' if kept.empty?
    # The current editor requires segments with at least two images.
    raise ArgumentError, 'a retained fragment has only one image; adjust the outer bounds' if kept.any? { |a, b| a == b }

    {
      'format' => 'video_encoder.trim_project', 'version' => 2,
      'sources' => [{ 'id' => 'source', 'path' => report.fetch('source') }],
      'timeline' => kept.map do |a, b|
        { 'type' => 'segment', 'source_id' => 'source', 'start_frame' => a, 'end_frame' => b }
      end
    }
  end

  def run(argv)
    options = {}
    OptionParser.new do |parser|
      parser.on('--report PATH') { |value| options[:report] = value }
      parser.on('--output PATH') { |value| options[:output] = value }
      parser.on('--expected-source PATH') { |value| options[:expected_source] = value }
      parser.on('--start-frame N', Integer) { |value| options[:first] = value }
      parser.on('--end-frame N', Integer) { |value| options[:last] = value }
    end.parse!(argv)
    raise ArgumentError, '--report and --output are required' unless options[:report] && options[:output]

    report_path = File.expand_path(options[:report])
    report_bytes = File.binread(report_path)
    report = JSON.parse(report_bytes)
    document = build(report, first: options.fetch(:first, 0), last: options[:last])
    source = report.fetch('source')
    raise ArgumentError, "source unavailable: #{source}" unless File.file?(source)
    if options[:expected_source] && File.realpath(options[:expected_source]) != File.realpath(source)
      raise ArgumentError, 'the report belongs to a different source'
    end

    manifest = JSON.parse(File.read(File.join(File.dirname(report_path), 'window-cache.json')))
    signature = manifest.fetch('source_signature')
    unless signature.length == 3 && signature[0] == source && signature[1] == File.size(source) && (signature[2] - File.mtime(source).to_f).abs < 0.001 && manifest['decoded_frames'] == report['decoded_frames']
      raise ArgumentError, 'source has changed or cache does not match this report; repeat analysis'
    end
    probe, error, status = Open3.capture3('ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', source)
    raise "ffprobe failed: #{error}" unless status.success?

    media = JSON.parse(probe)
    video = media.fetch('streams').find { |stream| stream['codec_type'] == 'video' }
    raise ArgumentError, 'source average frame rate must be 25 fps for this pilot' unless video && Rational(video.fetch('avg_frame_rate')) == 25

    destination = File.expand_path(options[:output])
    review_path = "#{destination}.review.json"
    raise ArgumentError, 'output must end in .json' unless File.extname(destination) == '.json'
    raise ArgumentError, 'destination is an input file' if [source, report_path].include?(destination)
    raise ArgumentError, 'destination or review file already exists' if File.exist?(destination) || File.exist?(review_path)

    review = {
      format: 'video_encoder.ad_trim_proposal_review', version: 1,
      status: 'needs_manual_review', generated_at: Time.now.iso8601,
      source_signature: signature, input_report: report_path,
      input_report_sha256: Digest::SHA256.hexdigest(report_bytes),
      proposed_project: destination, project_sha256: Digest::SHA256.hexdigest(JSON.pretty_generate(document) + "\n"),
      source_decoded_frame_count: report['decoded_frames'],
      proposed_exclusions: report['advertising_interval_hypotheses'],
      retained_frame_count: document['timeline'].sum { |item| item['end_frame'] - item['start_frame'] + 1 },
      outer_bounds: [document['timeline'].first['start_frame'], document['timeline'].last['end_frame']],
      review_instructions: [
        'The margins of the capture are retained by default; set the episode start and end manually.',
        'Review every proposed join before exporting. These cuts are experimental hypotheses.',
        'Unpaired candidates are not removed. No existing montage or capture is modified.',
        'This sidecar records the initial proposal; it is not updated when the editor saves the project.'
      ]
    }
    FileUtils.mkdir_p(File.dirname(destination))
    File.open(review_path, File::WRONLY | File::CREAT | File::EXCL) { |file| file.write(JSON.pretty_generate(review) + "\n") }
    File.open(destination, File::WRONLY | File::CREAT | File::EXCL) { |file| file.write(JSON.pretty_generate(document) + "\n") }
    puts JSON.generate(project: destination, review: review_path, segments: document['timeline'].length,
                       proposed_cuts: report['advertising_interval_hypotheses'].length, status: 'needs_manual_review')
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    AdTrimProposal.run(ARGV)
  rescue ArgumentError, KeyError, JSON::ParserError, Errno::ENOENT => error
    warn "#{error.class}: #{error.message}"
    exit 1
  end
end
