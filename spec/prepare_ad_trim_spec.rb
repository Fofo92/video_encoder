# frozen_string_literal: true

require 'tmpdir'
require_relative '../script/prepare_ad_trim'

RSpec.describe PrepareAdTrim do
  it 'does not refine a completed scan without candidates or claim a cut project exists' do
    Dir.mktmpdir do |workspace|
      report = File.join(workspace, 'detection', 'pub-candidates.json')
      allow(described_class).to receive(:run_detection) do
        FileUtils.mkdir_p(File.dirname(report))
        File.write(report, JSON.generate(format: 'video_encoder.6ter_pub_candidates', version: 3,
                                         complete: true, ffmpeg_exit_status: 0, candidate_count: 0, candidates: []))
      end
      expect(described_class).not_to receive(:run_refinement)
      expect(described_class).not_to receive(:run_proposal)
      expect { described_class.run_pipeline('/Braveheart.m2t', 10, 100, workspace) }
        .to output(/"status":"no_candidates"/).to_stdout
      expect(File.exist?(File.join(workspace, 'proposal.json'))).to be(false)
    end
  end
end
