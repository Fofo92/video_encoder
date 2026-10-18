# frozen_string_literal: true

require 'optparse'
require_relative '../lib/video_encoder/ad_detection/comskip_cut_list'
require_relative '../lib/video_encoder/ad_detection/comskip_project'
require_relative '../lib/video_encoder/ad_detection/comskip_execution'
require_relative '../lib/video_encoder/ad_detection/comskip_analysis'
require_relative '../lib/video_encoder/ad_detection/reference_evaluation'

# Analyse first; compare optional human references only after detection finishes.
module EvaluateComskip
  module_function

  def run(argv)
    options = { first: 0 }
    parser = OptionParser.new do |p|
      p.banner = 'ruby script/evaluate_comskip.rb --source FILE --workspace NEW_DIR [--reference JSON]'
      p.on('--source FILE') { |value| options[:source] = value }
      p.on('--workspace DIR') { |value| options[:workspace] = value }
      p.on('--reference JSON') { |value| options[:reference] = value }
      p.on('--recover-complete-output', 'Reuse complete TXT after an adapter failure; retain manual review') do
        options[:recover_complete_output] = true
      end
      p.on('--start-frame N', Integer) do |value|
        options[:first] = value
        options[:first_explicit] = true
      end
      p.on('--end-frame N', Integer) { |value| options[:last] = value }
    end
    parser.parse!(argv)
    raise ArgumentError, parser.to_s unless argv.empty? && options[:source] && options[:workspace]

    prepare(options)
  end

  def prepare(options)
    source = File.realpath(options.fetch(:source))
    workspace = File.expand_path(options.fetch(:workspace))
    analysis = VideoEncoder::AdDetection::ComskipAnalysis.new(profile: File.expand_path(
      '../config/comskip-generic.ini', __dir__
    ))
    cuts, observation, reused = analysis.call(source: source, workspace: workspace,
                                              recover_complete_output: options.fetch(:recover_complete_output, false))
    review = { needs_manual_review: true, reused_analysis: reused,
               analysis_seconds: observation.fetch('elapsed_seconds'),
               recovered_output: observation.fetch('recovered_output', false),
               native_frame_rate: observation.fetch('native_frame_rate', observation.fetch('frame_rate')),
               project_frame_rate: cuts.frame_rate.to_s,
               proposed_intervals: cuts.intervals.size, scanned_frame_count: cuts.frame_count }
    review[:evaluation] = evaluate(options, source, cuts) if options[:reference]
    write_draft(options, source, workspace, cuts, review)
    puts JSON.pretty_generate(review)
  end

  def evaluate(options, source, cuts)
    reference = JSON.parse(File.read(options.fetch(:reference)))
    VideoEncoder::AdDetection::ReferenceEvaluation.new(reference: reference, source: source, cut_list: cuts).call
  end

  def write_draft(options, source, workspace, cuts, review)
    project = VideoEncoder::AdDetection::ComskipProject.new(source: source, cut_list: cuts,
                                                            first: options[:first], last: options[:last]).call
    path = File.join(workspace, "proposal-#{options[:first]}-#{options[:last] || (cuts.frame_count - 1)}.json")
    bytes = "#{JSON.pretty_generate(project)}\n"
    unless File.file?(path) && File.binread(path) == bytes
      File.open(path, File::WRONLY | File::CREAT | File::EXCL) { |file| file.write(bytes) }
    end
    review[:project] = path
    review[:outer_bounds_assumed] = !options[:last] || !options.key?(:first_explicit)
  rescue ArgumentError => e
    review[:project] = nil
    review[:review_blocker] = e.message
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    EvaluateComskip.run(ARGV)
  rescue StandardError => e
    warn "#{e.class}: #{e.message}"
    exit 1
  end
end
