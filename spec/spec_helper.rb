# frozen_string_literal: true

require 'video_encoder'

RSpec.configure do |config|
  config.order = :random
  config.expect_with :rspec do |c|
    c.syntax = :expect
  end
end
