# frozen_string_literal: true

module DatabaseHelper
  def test_db
    @test_db ||= VideoEncoder::Persistence::Database.connect(':memory:')
  end
end
