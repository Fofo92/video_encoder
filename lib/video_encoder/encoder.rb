# frozen_string_literal: true

# Namespace for video encoding functionality.
module VideoEncoder
  # Base class for video encoder implementations.
  module Encoder
  end
end

require_relative 'encoder/base'
require_relative 'encoder/fake_encoder'
require_relative 'encoder/ffmpeg_encoder'
