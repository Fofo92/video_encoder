#!/usr/bin/env ruby
# frozen_string_literal: true

# Orchestrate the frozen experimental 6ter pilot. Does not export media.
require 'json'
require 'optparse'
require 'open3'
require 'fileutils'
require 'pathname'

# Orchestrates the experimental 6ter detection and proposal pipeline.
module PrepareAdTrim
  module_function

  def run(argv)
    options = {}
    parser = OptionParser.new do |p|
      p.banner = 'Usage: ruby script/prepare_ad_trim.rb --source FILE --workspace DIR --start-frame N --end-frame N'
      p.on('--source PATH') { |v| options[:source] = v }
      p.on('--workspace PATH') { |v| options[:workspace] = v }
      p.on('--start-frame N', Integer) { |v| options[:first] = v }
      p.on('--end-frame N', Integer) { |v| options[:last] = v }
      p.on('-h', '--help') { options[:help] = true }
    end
    parser.parse!(argv)
    if options[:help]
      puts parser
      return
    end

    unless argv.empty? && %i[source workspace first last].all? { |key| options.key?(key) }
      raise ArgumentError, parser.to_s
    end

    source, first, last, workspace = validate_request(options)
    run_pipeline(source, first, last, workspace)
  end

  def validate_request(options)
    source = File.realpath(options.fetch(:source))
    raise ArgumentError, 'source must be a regular file' unless File.file?(source)

    first = options.fetch(:first)
    last = options.fetch(:last)
    raise ArgumentError, 'invalid IN/OUT bounds' unless first >= 0 && last > first

    workspace = File.expand_path(options.fetch(:workspace))
    raise ArgumentError, 'workspace must not exist (avoid overwriting analysis)' if File.exist?(workspace)
    raise ArgumentError, 'workspace must not be inside the source path' if workspace == source

    [source, first, last, workspace]
  end

  def run_pipeline(source, first, last, workspace)
    scripts = File.join(__dir__, 'ad_detection')
    detection = File.join(workspace, 'detection')
    boundaries = File.join(workspace, 'boundaries')
    proposal = File.join(workspace, 'proposal.json')
    FileUtils.mkdir_p(workspace)
    begin
      run_detection(scripts, source, detection, workspace)
      run_refinement(scripts, detection, boundaries, workspace)
      run_proposal(source, first, last, boundaries, proposal, workspace)
      puts JSON.generate(status: 'needs_manual_review', project: proposal,
                         report: File.join(boundaries, 'boundary-hypotheses.json'))
    rescue StandardError, Interrupt
      warn "Preparation incomplete; diagnostics retained in #{workspace}"
      raise
    end
  end

  def run_detection(scripts, source, detection, workspace)
    execute(['ruby', File.join(scripts, 'detect_6ter_pub_v3.rb'),
             '--source', source, '--output', detection],
            File.join(workspace, 'detection.log'))
  end

  def run_refinement(scripts, detection, boundaries, workspace)
    execute(['ruby', File.join(scripts, 'refine_6ter_candidates_v4.rb'),
             '--candidates', File.join(detection, 'pub-candidates.json'),
             '--output', boundaries], File.join(workspace, 'refinement.log'))
  end

  def run_proposal(source, first, last, boundaries, proposal, workspace)
    execute(['ruby', File.join(__dir__, 'propose_ad_trim.rb'),
             '--report', File.join(boundaries, 'boundary-hypotheses.json'),
             '--expected-source', source, '--start-frame', first.to_s,
             '--end-frame', last.to_s, '--output', proposal],
            File.join(workspace, 'proposal.log'))
  end

  def execute(command, log_path)
    File.open(log_path, 'w') do |log|
      Open3.popen2e(*command) do |stdin, output, wait|
        stdin.close
        output.each_line do |line|
          log.write(line)
          $stderr.write(line)
        end
        raise "Command failed (#{wait.value.exitstatus}): #{command[1]}" unless wait.value.success?
      end
    end
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    PrepareAdTrim.run(ARGV)
  rescue StandardError => e
    warn "#{e.class}: #{e.message}"
    exit 1
  rescue Interrupt
    exit 130
  end
end
