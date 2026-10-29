# frozen_string_literal: true

require_relative '../../lib/video_encoder/cli/move_project_command'

RSpec.describe VideoEncoder::MoveProjectCommand do
  let(:database) { double('database') }
  let(:relocation) { instance_double(VideoEncoder::ProjectRelocation) }

  before { allow(VideoEncoder::ProjectRelocation).to receive(:new).with(database).and_return(relocation) }

  it 'keeps the existing move command compatible' do
    expect(relocation).to receive(:call).with('/old/a.json', '/new').and_return('/new/a.json')
    expect { described_class.new(argv: ['/old/a.json', '--directory', '/new'], database: database).run }
      .to output("/new/a.json\n").to_stdout
  end

  it 'passes a name with spaces and punctuation and returns a JSON preview' do
    expect(relocation).to receive(:call).with('/old/a.json', '/old', name: 'A : B & C', preview: true)
                                        .and_return({ format: 'video_encoder.project_relocation' })
    argv = ['/old/a.json', '--directory', '/old', '--name', 'A : B & C', '--preview']
    expect { described_class.new(argv: argv, database: database).run }
      .to output("{\"format\":\"video_encoder.project_relocation\"}\n").to_stdout
    expect(argv.last).to eq('--preview')
  end

  it 'rejects an unknown option before calling the relocation service' do
    expect(relocation).not_to receive(:call)
    expect do
      expect { described_class.new(argv: ['a.json', '--unknown'], database: database).run }
        .to raise_error(SystemExit)
    end.to output(/invalid option/).to_stderr
  end
end
