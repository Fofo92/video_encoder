# frozen_string_literal: true

require 'simplecov'

SimpleCov.start do
  add_filter '/spec/'
end

require 'video_encoder'

RSpec.configure do |config|
  config.order = :random
  config.expect_with :rspec do |c|
    c.syntax = :expect
  end
end

Dir[File.join(__dir__, 'support/**/*.rb')].sort.each do |file|
  require file
end

RSpec.configure do |config|
  config.include DatabaseHelper
end
