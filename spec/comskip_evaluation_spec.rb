# frozen_string_literal: true

require 'tmpdir'
require 'stringio'
require_relative '../script/evaluate_comskip'
require_relative '../lib/video_encoder/ad_detection/comskip_cut_list'
require_relative '../lib/video_encoder/ad_detection/comskip_project'
require_relative '../lib/video_encoder/ad_detection/comskip_execution'
require_relative '../lib/video_encoder/ad_detection/comskip_analysis'
require_relative '../lib/video_encoder/ad_detection/reference_evaluation'

RSpec.describe 'Generic detector evaluation' do
  def parse(rows = '', count: 200_000, rate: 2500)
    VideoEncoder::AdDetection::ComskipCutList.new("FILE PROCESSING COMPLETE #{count} FRAMES AT #{rate}\n-----\n#{rows}")
  end

  it 'converts one-based inclusive Comskip frames into the editor frame convention' do
    cuts = parse("105333 110466\n171243 176612\n")
    expect(cuts.intervals).to eq([[105_332, 110_465], [171_242, 176_611]])
    project = VideoEncoder::AdDetection::ComskipProject.new(source: '/capture.m2t', cut_list: cuts,
                                                            first: 100, last: 190_000).call
    expect(project[:timeline].map { |row| [row[:start_frame], row[:end_frame]] })
      .to eq([[100, 105_331], [110_466, 171_241], [176_612, 190_000]])
  end

  it 'clips detected commercials to the manual outer bounds and merges adjacent exclusions' do
    cuts = parse("1 150\n151 200\n901 1000\n", count: 1000)
    project = VideoEncoder::AdDetection::ComskipProject.new(source: '/capture.m2t', cut_list: cuts,
                                                            first: 100, last: 950).call
    expect(project[:timeline].map { |row| [row[:start_frame], row[:end_frame]] }).to eq([[200, 899]])
  end

  it 'converts the real Braveheart 50 Hz export into conservative 25 fps exclusions' do
    native = parse("7635 15623\n17637 28147\n210667 221243\n342433 353381\n" \
                   "544141 555991\n558763 563513\n614903 614905\n", count: 614_905, rate: 5000)
    cuts = VideoEncoder::AdDetection::ComskipCoordinates.convert(native, Rational(25))
    expect(cuts.frame_rate).to eq(Rational(25))
    expect(cuts.frame_count).to eq(307_452)
    expect(cuts.intervals[2..3]).to eq([[105_333, 110_620], [171_216, 176_689]])
    expect(cuts.intervals.last).to eq([307_451, 307_451])
    expect(native.frame_count).to eq(614_905)
  end

  it 'does not exclude programme frames only partially covered in field coordinates' do
    native = parse("2 3\n6 8\n", count: 1000, rate: 5000)
    cuts = VideoEncoder::AdDetection::ComskipCoordinates.convert(native, Rational(25))
    expect(cuts.intervals).to eq([[3, 3]])
    expect { VideoEncoder::AdDetection::ComskipCoordinates.convert(native, Rational(24)) }
      .to raise_error(/unsupported coordinate conversion/)
  end

  it 'keeps an uncut draft for a complete result without commercial intervals' do
    project = VideoEncoder::AdDetection::ComskipProject.new(source: '/capture.m2t', cut_list: parse,
                                                            first: 100, last: 1000).call
    expect(project[:timeline].map { |row| [row[:start_frame], row[:end_frame]] }).to eq([[100, 1000]])
  end

  it 'rejects malformed, overlapping, unsorted and out-of-range results' do
    ['0 20', '10 200001', "10 20\n15 30", "100 200\n1 10", '10 5', 'error'].each do |rows|
      expect { parse(rows) }.to raise_error(ArgumentError)
    end
    expect { VideoEncoder::AdDetection::ComskipCutList.new('unfinished') }.to raise_error(ArgumentError)
  end

  it 'does not fabricate a montage if all content is excluded or one frame is left' do
    [parse('1 1000', count: 1000), parse('2 1000', count: 1000)].each do |cuts|
      expect { VideoEncoder::AdDetection::ComskipProject.new(source: '/source', cut_list: cuts).call }
        .to raise_error(ArgumentError)
    end
  end

  it 'compares the known NOVO19 breaks without treating unlabelled proposals as errors' do
    reference = JSON.parse(File.read(File.expand_path('../config/ad_detection/braveheart-novo19.reference.json',
                                                      __dir__)))
    cuts = parse("1001 2000\n105333 110466\n171243 176612\n")
    report = VideoEncoder::AdDetection::ReferenceEvaluation.new(reference: reference,
                                                                source: reference.fetch('source'), cut_list: cuts).call
    expect(report[:matched_known_intervals]).to eq(2)
    expect(report[:proposed_intervals]).to eq(3)
    expect(report[:intervals].map { |row| row[:error_frames] }).to eq([[0, 0], [0, 0]])
    expect(report[:coverage]).to eq('known_intervals_only')
  end

  it 'reports missing and imprecise known boundaries rather than declaring a reliable result' do
    reference = { 'format' => 'video_encoder.ad_reference', 'version' => 1, 'coverage' => 'known_intervals_only',
                  'source' => '/capture', 'frame_rate' => '25/1', 'excluded_intervals' => [[100, 200], [500, 700]] }
    report = VideoEncoder::AdDetection::ReferenceEvaluation.new(reference: reference, source: '/capture',
                                                                cut_list: parse('151 251', count: 1000)).call
    expect(report[:matched_known_intervals]).to eq(0)
    expect(report[:intervals][0][:error_frames]).to eq([50, 50])
    expect(report[:intervals][1][:proposed]).to be_nil
  end

  describe 'reusable observations' do
    around do |example|
      Dir.mktmpdir do |directory|
        @source = File.join(directory, 'capture.m2t')
        @workspace = File.join(directory, 'analysis')
        @profile = File.join(directory, 'profile.ini')
        File.write(@source, 'capture')
        File.write(@profile, 'detect_method=111')
        example.run
      end
    end

    def analysis
      @execution = instance_double(VideoEncoder::AdDetection::ComskipExecution, version: 'Comskip test',
                                                                                frame_rate: Rational(25))
      allow(@execution).to receive(:call) do |_source, workspace|
        File.write("#{workspace}/analysis.txt", "FILE PROCESSING COMPLETE 1000 FRAMES AT 2500\n-----\n201 300\n")
      end
      VideoEncoder::AdDetection::ComskipAnalysis.new(profile: @profile, execution: @execution)
    end

    it 'analyses once and reuses unchanged observations without rerunning the engine' do
      detector = analysis
      _cuts, _report, reused = detector.call(source: @source, workspace: @workspace)
      expect(reused).to be(false)
      _cuts, report, reused = detector.call(source: @source, workspace: @workspace)
      expect(reused).to be(true)
      expect(report['needs_manual_review']).to be(true)
      expect(@execution).to have_received(:call).once
      expect(File.read(@source)).to eq('capture')
    end

    it 'rejects a source changed after analysis and preserves all diagnostics' do
      detector = analysis
      detector.call(source: @source, workspace: @workspace)
      File.write(@source, 'new capture')
      expect { detector.call(source: @source, workspace: @workspace) }.to raise_error(ArgumentError)
      expect(File.exist?("#{@workspace}/analysis.txt")).to be(true)
      expect(@execution).to have_received(:call).once
    end

    it 'rejects a hand-modified cached result or changed profile' do
      detector = analysis
      detector.call(source: @source, workspace: @workspace)
      File.write("#{@workspace}/analysis.txt", 'changed')
      expect { detector.call(source: @source, workspace: @workspace) }.to raise_error(ArgumentError)
      File.write(@profile, 'detect_method=1')
      changed = VideoEncoder::AdDetection::ComskipAnalysis.new(profile: @profile, execution: @execution)
      expect { changed.call(source: @source, workspace: @workspace) }.to raise_error(ArgumentError)
    end

    it 'does not mark the observation complete when its time base differs from the source' do
      detector = analysis
      allow(@execution).to receive(:frame_rate).and_return(Rational(50))
      expect { detector.call(source: @source, workspace: @workspace) }.to raise_error(/frame rate differs/)
      expect(File.exist?("#{@workspace}/analysis.json")).to be(false)
    end

    it 'does not accept a complete-looking cut list after the engine fails' do
      detector = analysis
      allow(@execution).to receive(:call).and_raise('decoder failed')
      expect { detector.call(source: @source, workspace: @workspace) }.to raise_error(/decoder failed/)
      expect(File.exist?("#{@workspace}/analysis.json")).to be(false)
    end

    it 'normalizes a fresh field-rate export and reuses it without another conversion or engine run' do
      detector = analysis
      allow(@execution).to receive(:call) do |_source, workspace|
        File.write("#{workspace}/analysis.txt", "FILE PROCESSING COMPLETE 2000 FRAMES AT 5000\n-----\n401 600\n")
      end
      cuts, report, = detector.call(source: @source, workspace: @workspace)
      expect(cuts.intervals).to eq([[200, 299]])
      expect(report['native_frame_rate']).to eq('50/1')
      cuts, _report, reused = detector.call(source: @source, workspace: @workspace)
      expect(reused).to be(true)
      expect(cuts.intervals).to eq([[200, 299]])
      expect(@execution).to have_received(:call).once
    end

    it 'explicitly recovers complete legacy output without rerunning the detector or inventing runtime' do
      detector = analysis
      allow(@execution).to receive(:frame_rate).and_return(Rational(24))
      expect { detector.call(source: @source, workspace: @workspace) }.to raise_error(/frame rate differs/)
      expect { detector.call(source: @source, workspace: @workspace) }.to raise_error(Errno::ENOENT)
      allow(@execution).to receive(:frame_rate).and_return(Rational(25))
      File.write("#{@workspace}/analysis.txt", "FILE PROCESSING COMPLETE 2000 FRAMES AT 5000\n-----\n401 600\n")
      cuts, report, reused = detector.call(source: @source, workspace: @workspace, recover_complete_output: true)
      expect(cuts.intervals).to eq([[200, 299]])
      expect(reused).to be(true)
      expect(report['recovered_output']).to be(true)
      expect(report['elapsed_seconds']).to be_nil
      expect(report['needs_manual_review']).to be(true)
      expect(@execution).to have_received(:call).once
    end

    it 'rejects recovery after source changes, profile changes or an incomplete native export' do
      detector = analysis
      allow(@execution).to receive(:call).and_raise('interrupted')
      expect { detector.call(source: @source, workspace: @workspace) }.to raise_error(/interrupted/)
      File.write("#{@workspace}/analysis.txt", 'incomplete')
      expect { detector.call(source: @source, workspace: @workspace, recover_complete_output: true) }
        .to raise_error(/incomplete/)
      File.write("#{@workspace}/comskip.ini", 'changed')
      expect { detector.call(source: @source, workspace: @workspace, recover_complete_output: true) }
        .to raise_error(/has changed/)
      File.write("#{@workspace}/comskip.ini", 'detect_method=111')
      File.write(@source, 'changed capture')
      expect { detector.call(source: @source, workspace: @workspace, recover_complete_output: true) }
        .to raise_error(/has changed/)
      expect(File.exist?("#{@workspace}/analysis.json")).to be(false)
      expect(@execution).to have_received(:call).once
    end

    it 'accepts the recovery CLI option and writes a project in source-frame coordinates' do
      detector = analysis
      allow(@execution).to receive(:frame_rate).and_return(Rational(24))
      expect { detector.call(source: @source, workspace: @workspace) }.to raise_error(/frame rate differs/)
      allow(@execution).to receive(:frame_rate).and_return(Rational(25))
      File.write("#{@workspace}/analysis.txt", "FILE PROCESSING COMPLETE 2000 FRAMES AT 5000\n-----\n401 600\n")
      allow(VideoEncoder::AdDetection::ComskipAnalysis).to receive(:new).and_return(detector)
      output = StringIO.new
      original_stdout = $stdout
      $stdout = output
      EvaluateComskip.run(['--source', @source, '--workspace', @workspace, '--recover-complete-output'])
      review = JSON.parse(output.string)
      expect(review['recovered_output']).to be(true)
      expect(review['project_frame_rate']).to eq('25/1')
      project = JSON.parse(File.read(review.fetch('project')))
      expect(project['timeline'].map { |row| [row['start_frame'], row['end_frame']] })
        .to eq([[0, 199], [300, 999]])
      expect(@execution).to have_received(:call).once
    ensure
      $stdout = original_stdout
    end
  end
end
