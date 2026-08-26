# frozen_string_literal: true

require 'open3'
require 'tmpdir'
require 'spec_helper'

RSpec.describe 'bin/video_encoder_ccextractor' do
  let(:launcher) do
    File.expand_path('../bin/video_encoder_ccextractor', __dir__)
  end

  it 'runs the default image without a volume for an informational command' do
    with_fake_docker do |environment, arguments_path|
      _stdout, stderr, status = Open3.capture3(
        environment,
        launcher,
        '--version'
      )

      expect(status).to be_success
      expect(stderr).to eq('')
      expect(read_arguments(arguments_path)).to eq(
        [
          'run',
          '--rm',
          '--pull',
          'never',
          '--network',
          'none',
          'video-encoder-ccextractor:0.96.6-ocr-fra',
          '--version'
        ]
      )
    end
  end

  it 'mounts the output directory for an OCR command' do
    with_fake_docker do |environment, arguments_path|
      workspace = File.join(environment.fetch('TEST_DIRECTORY'), 'workspace')
      input_path = File.join(workspace, 'segment.ts')
      output_path = File.join(workspace, 'segment.srt')

      Dir.mkdir(workspace)

      _stdout, stderr, status = Open3.capture3(
        environment,
        launcher,
        '--out',
        'srt',
        input_path,
        '-o',
        output_path
      )

      expect(status).to be_success
      expect(stderr).to eq('')
      expect(read_arguments(arguments_path)).to eq(
        [
          'run',
          '--rm',
          '--pull',
          'never',
          '--network',
          'none',
          '--user',
          "#{Process.uid}:#{Process.gid}",
          '--volume',
          "#{workspace}:#{workspace}",
          'video-encoder-ccextractor:0.96.6-ocr-fra',
          '--out',
          'srt',
          input_path,
          '-o',
          output_path
        ]
      )
    end
  end

  it 'allows the image to be overridden' do
    with_fake_docker do |environment, arguments_path|
      environment['VIDEO_ENCODER_CCEXTRACTOR_IMAGE'] =
        'video-encoder-ccextractor:0.96.5-ocr-fra-reference'

      _stdout, _stderr, status = Open3.capture3(
        environment,
        launcher,
        '--version'
      )

      expect(status).to be_success
      expect(read_arguments(arguments_path)).to include(
        'video-encoder-ccextractor:0.96.5-ocr-fra-reference'
      )
    end
  end

  it 'propagates a Docker failure' do
    with_fake_docker do |environment, _arguments_path|
      environment['DOCKER_EXIT_STATUS'] = '125'
      environment['DOCKER_ERROR'] = 'docker: image not found'

      _stdout, stderr, status = Open3.capture3(
        environment,
        launcher,
        '--version'
      )

      expect(status.exitstatus).to eq(125)
      expect(stderr).to eq("docker: image not found\n")
    end
  end

  def with_fake_docker
    Dir.mktmpdir do |directory|
      arguments_path = File.join(directory, 'docker_arguments')
      docker_path = File.join(directory, 'docker')

      File.write(
        docker_path,
        <<~SH
          #!/bin/sh
          printf '%s\\n' "$@" > "$DOCKER_ARGUMENTS_PATH"
          if [ -n "${DOCKER_ERROR:-}" ]; then
            printf '%s\n' "$DOCKER_ERROR" >&2
          fi

          exit "${DOCKER_EXIT_STATUS:-0}"
        SH
      )
      File.chmod(0o755, docker_path)

      environment = {
        'PATH' => "#{directory}:#{ENV.fetch('PATH')}",
        'DOCKER_ARGUMENTS_PATH' => arguments_path,
        'TEST_DIRECTORY' => directory,
        'VIDEO_ENCODER_WORKSPACE' => nil
      }

      yield environment, arguments_path
    end
  end

  def read_arguments(path)
    File.readlines(path, chomp: true)
  end
end
