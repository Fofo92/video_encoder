# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'
require_relative '../lib/video_encoder/project_relocation'

RSpec.describe VideoEncoder::CopyVersionReplacement do
  it 'routes only reclaiming the source name through the replacement helper' do
    Dir.mktmpdir do |directory|
      project = File.join(directory, 'Film - VOST.json')
      File.write(project, JSON.generate(format: 'video_encoder.copy_version',
                                        version_change: { source_path: File.join(directory, 'Film.mkv') }))
      service = described_class.new(double('database'))
      expect(service.applies?(project, directory, 'Film')).to be(true)
      expect(service.applies?(project, directory, 'Another')).to be(false)
      expect(service.applies?(project, directory, '../Film')).to be(false)
      expect(service.applies?(project, directory, nil)).to be(false)
    end
  end

  it 'passes unicode paths and SQLite scope as distinct arguments and decodes the read-only preview' do
    Dir.mktmpdir do |directory|
      database = File.join(directory, 'queue.sqlite3')
      File.write(database, '')
      service = described_class.new(double('database', opts: { database: database }))
      status = double('status', success?: true)
      allow(Open3).to receive(:capture3).and_return(['{"format":"video_encoder.project_relocation"}', '', status])
      result = service.call('/videos/Épisode - VOST.json', directory, 'Épisode', preview: true)
      expect(result[:format]).to eq('video_encoder.project_relocation')
      expect(Open3).to have_received(:capture3).with(
        'python3', end_with('copy_version_replacement.py'), database, '/videos/Épisode - VOST.json',
        directory, 'Épisode', 'preview'
      )
    end
  end

  it 'refuses helper failures instead of falling back to an unsafe rename' do
    Dir.mktmpdir do |directory|
      database = File.join(directory, 'queue.sqlite3')
      File.write(database, '')
      service = described_class.new(double('database', opts: { database: database }))
      allow(Open3).to receive(:capture3).and_return(['', 'Une tâche utilise encore le projet.',
                                                     double('status', success?: false)])
      expect { service.call('/videos/Film - VOST.json', directory, 'Film', preview: false) }
        .to raise_error(VideoEncoder::ProjectRelocationError, /tâche/)
    end
  end
end
