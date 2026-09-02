# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'

RSpec.describe VideoEncoder::Persistence::Database do
  describe '.connect' do
    it 'creates the jobs schema in a new database' do
      Dir.mktmpdir do |directory|
        path = File.join(directory, 'video_encoder.db')
        database = described_class.connect(path)

        expect(database.table_exists?(:jobs)).to be(true)
        columns = database.schema(:jobs).map(&:first)

        expect(columns).to include(
          :kind,
          :source,
          :project_path,
          :output_path
        )

        database[:jobs].insert(
          job_id: 'job-1',
          source: 'video.m2t'
        )

        expect(database[:jobs].first).to include(
          job_id: 'job-1',
          kind: 'encoding',
          source: 'video.m2t',
          project_path: nil,
          output_path: nil,
          attempts: 0
        )

        expect do
          database[:jobs].insert(job_id: 'job-1')
        end.to raise_error(Sequel::UniqueConstraintViolation)

        database.disconnect
      end
    end

    it 'connects independently to different database files' do
      Dir.mktmpdir do |directory|
        first = described_class.connect(
          File.join(directory, 'first.db')
        )
        second = described_class.connect(
          File.join(directory, 'second.db')
        )

        first[:jobs].insert(job_id: 'job-1')

        expect(first[:jobs].count).to eq(1)
        expect(second[:jobs].count).to eq(0)

        first.disconnect
        second.disconnect
      end
    end

    it 'classifies existing jobs as encoding jobs' do
      Dir.mktmpdir do |directory|
        path = File.join(
          directory,
          'video_encoder.db'
        )

        legacy_database = Sequel.sqlite(path)

        Sequel::Migrator.run(
          legacy_database,
          described_class::MIGRATIONS_PATH,
          target: 1
        )

        legacy_database[:jobs].insert(
          job_id: 'legacy-job',
          source: 'legacy.m2t',
          status: 'done',
          attempts: 1
        )
        legacy_database.disconnect

        database = described_class.connect(path)
        job = database[:jobs].first

        expect(database[:jobs].count).to eq(1)
        expect(job).to include(
          job_id: 'legacy-job',
          kind: 'encoding',
          source: 'legacy.m2t',
          project_path: nil,
          output_path: nil,
          status: 'done',
          attempts: 1
        )

        database.disconnect
      end
    end
  end
end
