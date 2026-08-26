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

        database[:jobs].insert(job_id: 'job-1')

        expect(database[:jobs].first).to include(
          job_id: 'job-1',
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
  end
end
