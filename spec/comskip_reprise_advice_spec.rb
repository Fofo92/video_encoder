# frozen_string_literal: true

require 'tmpdir'
require_relative '../script/evaluate_comskip'

RSpec.describe 'Experimental Comskip reprise advice' do
  let(:source) { '/commun/to_be_cut/9-1-1 - S05 E15 - Les signes du destin.m2t' }
  let(:text) { File.read(File.expand_path('fixtures/ad_detection/911-s05e15-evidence.log', __dir__)) }
  let(:cuts) do
    native = VideoEncoder::AdDetection::ComskipCutList.new(
      "FILE PROCESSING COMPLETE 209963 FRAMES AT 5000\n-----\n" \
      "1 7301\n23099 26843\n60047 74905\n140157 158801\n183403 209963\n"
    )
    VideoEncoder::AdDetection::ComskipCoordinates.convert(native, Rational(25))
  end

  def advise(log = text)
    evidence = VideoEncoder::AdDetection::ComskipEvidence.new(log, source: source, rate: Rational(25))
    VideoEncoder::AdDetection::ComskipRepriseAdvice.new(evidence: evidence, cut_list: cuts,
                                                        first: 13_405, last: 92_044).call
  end

  it 'proposes two local transitions from real traces without accepting human reference bounds as inputs' do
    suggestions = advise
    expect(suggestions.map { |row| row[:current_resume] }).to eq([37_452, 79_400])
    expect(suggestions.map { |row| row[:suggested_resume] }).to eq([37_966, 79_550])
    expect(suggestions.map { |row| row[:shift_frames] }).to eq([514, 150])
    expect(suggestions).to all(include(needs_manual_review: true))
  end

  it 'abstains when multiple strong transitions precede the same stable logo return' do
    extra = "\nFrame 38000 (1519.920s) - Black frame because large scene change of 98, uniform 5000\n"
    expect(advise(text + extra).first[:suggested_resume]).to be_nil
  end

  it 'abstains when the logo evidence is missing, short or too distant' do
    expect(advise(text.gsub('0:03:52.00', '0:00:12.00')).first[:suggested_resume]).to be_nil
    expect(advise(text.gsub('frame 38100', 'frame 40000')).first[:suggested_resume]).to be_nil
    expect(advise(text.lines.reject { |line| line.include?('logo') }.join).map { |row| row[:suggested_resume] })
      .to eq([nil, nil])
  end

  it 'rejects evidence from another source or another average frame rate' do
    expect { advise(text.sub(source, '/other.m2t')) }.to raise_error(/does not match/)
    expect { advise(text.sub('25.000', '30.000')) }.to raise_error(/does not match/)
  end

  it 'creates a separate review project and evaluates it only after generating the suggestions' do
    Dir.mktmpdir do |workspace|
      File.write("#{workspace}/analysis.log", text)
      File.write("#{workspace}/proposal-locked-13405-92044.json", 'original project')
      experiment = VideoEncoder::AdDetection::ComskipRepriseExperiment.new(
        source: source, workspace: workspace, cuts: cuts, first: 13_405, last: 92_044
      )
      report, refined = experiment.call
      project = JSON.parse(File.read(report[:project]))
      expect(report[:changed_reprises]).to eq(2)
      expect(project['timeline'].map { |row| [row['start_frame'], row['end_frame']] })
        .to eq([[13_405, 30_022], [37_966, 70_077], [79_550, 92_044]])
      expect(File.read("#{workspace}/proposal-locked-13405-92044.json")).to eq('original project')
      reference = JSON.parse(File.read(File.expand_path('../config/ad_detection/911-s05e15.reference.json', __dir__)))
      evaluation = VideoEncoder::AdDetection::ReferenceEvaluation.new(reference: reference, source: source,
                                                                      cut_list: refined).call
      expect(evaluation[:intervals].map { |row| row[:error_frames] }).to eq([[1, 4], [-5, 3]])
      expect(evaluation[:matched_known_intervals]).to eq(2)
      expect(experiment.call.first[:project]).to eq(report[:project])
      File.write(report[:project], 'manually edited alternative')
      expect(experiment.call.first[:status]).to eq('unavailable')
      expect(File.read(report[:project])).to eq('manually edited alternative')
    end
  end

  it 'keeps the baseline usable when the evidence is missing or has no unambiguous suggestion' do
    Dir.mktmpdir do |workspace|
      experiment = VideoEncoder::AdDetection::ComskipRepriseExperiment.new(
        source: source, workspace: workspace, cuts: cuts, first: 13_405, last: 92_044
      )
      expect(experiment.call.first[:status]).to eq('unavailable')
      File.write("#{workspace}/analysis.log", "Mpeg:\t#{source}\nAverage framerate: 25.000\n")
      report, = experiment.call
      expect(report[:changed_reprises]).to eq(0)
      expect(report[:project]).to be_nil
    end
  end

  it 'requires explicit manual outer bounds before enabling the experiment' do
    expect { EvaluateComskip.run(['--source', source, '--workspace', '/unused', '--suggest-reprises']) }
      .to raise_error(/requires explicit/)
  end
end
