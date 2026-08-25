# frozen_string_literal: true

require 'spec_helper'
require 'fileutils'
require 'tmpdir'

RSpec.describe VideoEncoder::ExternalDependencyChecker do
  describe '#call' do
    it 'accepts an executable available in the configured path' do
      directory = Dir.mktmpdir('video_encoder_executables')
      executable = File.join(directory, 'ffmpeg')

      File.write(executable, "#!/bin/sh\n")
      FileUtils.chmod(0o755, executable)

      checker = described_class.new(path: directory)

      expect do
        checker.call('ffmpeg')
      end.not_to raise_error
    ensure
      FileUtils.remove_entry(directory) if directory && Dir.exist?(directory)
    end

    it 'accepts an executable identified by its path' do
      directory = Dir.mktmpdir('video_encoder_executables')
      executable = File.join(directory, 'ccextractor')

      File.write(executable, "#!/bin/sh\n")
      FileUtils.chmod(0o755, executable)

      checker = described_class.new(path: '')

      expect do
        checker.call(executable)
      end.not_to raise_error
    ensure
      FileUtils.remove_entry(directory) if directory && Dir.exist?(directory)
    end

    it 'reports every missing external dependency' do
      checker = described_class.new(path: '')

      expect do
        checker.call('ffmpeg', 'ffprobe', 'melt-7')
      end.to raise_error(
        VideoEncoder::MissingExternalDependenciesError,
        'missing external dependencies: ffmpeg, ffprobe, melt-7'
      )
    end

    it 'rejects a file without execution permission' do
      directory = Dir.mktmpdir('video_encoder_executables')
      executable = File.join(directory, 'ffmpeg')

      File.write(executable, "#!/bin/sh\n")
      FileUtils.chmod(0o644, executable)

      checker = described_class.new(path: directory)

      expect do
        checker.call('ffmpeg')
      end.to raise_error(VideoEncoder::MissingExternalDependenciesError,
                         'missing external dependencies: ffmpeg')
    ensure
      FileUtils.remove_entry(directory) if directory && Dir.exist?(directory)
    end
  end
end
