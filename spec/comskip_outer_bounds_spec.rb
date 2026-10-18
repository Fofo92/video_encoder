# frozen_string_literal: true

require 'tmpdir'
require 'stringio'
require_relative '../script/evaluate_comskip'

RSpec.describe 'Comskip manual outer bounds' do
  def cuts(rows, count: 104_981)
    text = "FILE PROCESSING COMPLETE #{count} FRAMES AT 2500\n-----\n#{rows}"
    VideoEncoder::AdDetection::ComskipCutList.new(text)
  end

  def draft(cut_list, **options)
    VideoEncoder::AdDetection::ComskipProject.new(source: '/capture.m2t', cut_list: cut_list,
                                                  first: 13_405, last: 92_044, **options)
  end

  def intervals(project)
    project.fetch(:timeline).map { |row| [row[:start_frame], row[:end_frame]] }
  end

  it 'keeps both manual endpoints and leaves internal detections unchanged' do
    detected = cuts("1 13421\n30024 37452\n70079 79400\n91702 104981\n")
    expect(intervals(draft(detected).call)).to eq([[13_421, 30_022], [37_452, 70_077], [79_400, 91_700]])
    locked = draft(detected, lock_outer_bounds: true)
    expect(intervals(locked.call)).to eq([[13_405, 30_022], [37_452, 70_077], [79_400, 92_044]])
    expect(locked.ignored_boundary_intervals).to eq([[0, 13_420], [91_701, 104_980]])
    expect(intervals(locked.call).first.first).to eq(13_405)
  end

  it 'protects an endpoint even when a detected interval starts exactly on it' do
    detected = cuts("13406 13426\n92040 92045\n")
    expect(intervals(draft(detected, lock_outer_bounds: true).call)).to eq([[13_405, 92_044]])
  end

  it 'blocks an all-commercial manual envelope instead of silently retaining everything' do
    expect { draft(cuts('1 104981'), lock_outer_bounds: true).call }.to raise_error(/entire manual envelope/)
  end

  it 'evaluates the true Comskip pauses against the corrected three-segment reference' do
    reference = JSON.parse(File.read(File.expand_path('../config/ad_detection/911-s05e15.reference.json', __dir__)))
    report = VideoEncoder::AdDetection::ReferenceEvaluation.new(
      reference: reference, source: reference.fetch('source'), cut_list: cuts("30024 37452\n70079 79400\n")
    ).call
    expect(report[:known_intervals]).to eq(2)
    expect(report[:intervals].map { |row| row[:error_frames] }).to eq([[1, -510], [-5, -147]])
    expect(report[:matched_known_intervals]).to eq(0)
  end

  it 'writes a separate locked proposal from cached analysis without overwriting an existing project' do
    Dir.mktmpdir do |directory|
      source = File.join(directory, 'capture.m2t')
      workspace = File.join(directory, 'analysis')
      File.write(source, 'capture')
      Dir.mkdir(workspace)
      old_path = File.join(workspace, 'proposal-13405-92044.json')
      File.write(old_path, 'previous reviewed project')
      detected = cuts("1 13421\n30024 37452\n70079 79400\n91702 104981\n")
      analysis = instance_double(VideoEncoder::AdDetection::ComskipAnalysis)
      observation = { 'elapsed_seconds' => 413.9, 'frame_rate' => '25/1' }
      allow(analysis).to receive(:call).and_return([detected, observation, true])
      allow(VideoEncoder::AdDetection::ComskipAnalysis).to receive(:new).and_return(analysis)
      output = StringIO.new
      original_stdout = $stdout
      $stdout = output
      arguments = ['--source', source, '--workspace', workspace, '--start-frame', '13405', '--end-frame', '92044']
      EvaluateComskip.run(arguments.dup)
      report = JSON.parse(output.string)
      expect(report['outer_bounds_locked']).to be(true)
      expect(report['project']).to end_with('proposal-locked-13405-92044.json')
      project = JSON.parse(File.read(report.fetch('project')))
      expect(project['timeline'].first['start_frame']).to eq(13_405)
      expect(project['timeline'].last['end_frame']).to eq(92_044)
      expect(File.read(old_path)).to eq('previous reviewed project')
      EvaluateComskip.run(arguments.dup)
      expect(File.read(old_path)).to eq('previous reviewed project')
    ensure
      $stdout = original_stdout
    end
  end
end
