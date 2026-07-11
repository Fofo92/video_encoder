# frozen_string_literal: true

require 'sequel'
require 'tmpdir'

module DatabaseHelper
  def test_db
    @test_db ||= begin
      # path = File.join(Dir.tmpdir, 'video_encoder_test.sqlite3')

      # File.delete(path) if File.exist?(path)

      db = Sequel.sqlite

      db.create_table :jobs do
        primary_key :id
        String   :job_id
        String   :source
        String   :status
        Integer  :attempts
        DateTime :created_at
        DateTime :started_at
        DateTime :finished_at
        String   :error
      end

      db
    end
  end
end
