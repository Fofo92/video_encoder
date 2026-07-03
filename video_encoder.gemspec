# frozen_string_literal: true

require_relative 'lib/video_encoder/version'

Gem::Specification.new do |spec|
  spec.name          = 'video_encoder'
  spec.version       = VideoEncoder::VERSION
  spec.summary       = 'Video encoding pipeline'
  spec.authors       = ['Pascal Fodiman']

  spec.files         = Dir['lib/**/*.rb'] + ['bin/video_encoder']
  spec.bindir        = 'bin'
  spec.executables   = ['video_encoder']

  spec.required_ruby_version = '>= 3.3'
end
