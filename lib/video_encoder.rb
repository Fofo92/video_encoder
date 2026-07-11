# frozen_string_literal: true

require 'pathname'
require 'securerandom'
require 'time'

require_relative 'video_encoder/version'
require_relative 'video_encoder/domain/status'
require_relative 'video_encoder/domain/job'

require_relative 'video_encoder/persistence/database'
require_relative 'video_encoder/persistence/job_repository'

require_relative 'video_encoder/encoder/base'
require_relative 'video_encoder/encoder/fake_encoder'
require_relative 'video_encoder/encoder/ffmpeg_runner'
require_relative 'video_encoder/encoder/ffmpeg_encoder'

require_relative 'video_encoder/worker'
require_relative 'video_encoder/cli'
require_relative 'video_encoder/loggable'
require_relative 'video_encoder/config'
require_relative 'video_encoder/directories'
require_relative 'video_encoder/ffmpeg_config'
require_relative 'video_encoder/watcher'
require_relative 'video_encoder/verifier'
require_relative 'video_encoder/cleaner'

require 'logger'
