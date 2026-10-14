# frozen_string_literal: true

RSpec.describe VideoEncoder::ActiveTrimExportSourceUsage do
  it 'continues to protect the source of a deferred task' do
    job = VideoEncoder::TrimExportJob.new(
      project_path: '/project.json', output_path: '/movie.mkv', status: VideoEncoder::Status::DEFERRED
    )
    reader = double('reader')
    allow(reader).to receive(:read).with(job.project_path).and_return('project')
    paths = double('paths')
    allow(paths).to receive(:call).with('project').and_return(['/capture.m2t'])
    usage = described_class.new(repo: double(all: [job]), reader: reader, source_paths: paths)
    expect(usage.call('/capture.m2t')).to eq([job])
  end
end
