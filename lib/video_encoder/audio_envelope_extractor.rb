# frozen_string_literal: true

require 'open3'

module VideoEncoder
  # Extracts the RMS envelope for an audio stream over fixed time intervals.
  class AudioEnvelopeExtractor
    class EnvelopeUnavailable < StandardError; end

    def initialize(
      interval_seconds:,
      sample_rate:,
      executor: Open3
    )
      @interval_seconds = interval_seconds
      @sample_rate = sample_rate
      @executor = executor
    end

    def call(
      path:,
      stream_index:,
      start_seconds:,
      duration_seconds:
    )
      command = command(
        path: path,
        stream_index: stream_index,
        start_seconds: start_seconds,
        duration_seconds: duration_seconds
      )

      stdout, stderr, status = executor.capture3(
        *command
      )

      unless status.success?
        failure = CommandRunner::CommandFailed.new(
          command: command,
          status: status
        )

        raise failure,
              "#{failure.message}\n#{stderr}"
      end

      if stdout.empty?
        raise EnvelopeUnavailable,
              'audio envelope is unavailable'
      end

      build_envelope(stdout.unpack('e*'))
    end

    private

    attr_reader :executor,
                :interval_seconds,
                :sample_rate

    def command(
      path:,
      stream_index:,
      start_seconds:,
      duration_seconds:
    )
      [
        'ffmpeg',
        '-hide_banner',
        '-nostdin',
        '-loglevel', 'error',
        '-ss', format('%.6f', start_seconds),
        '-i', path.to_s,
        '-t', format('%.6f', duration_seconds),
        '-map', "0:#{stream_index}",
        '-vn',
        '-sn',
        '-dn',
        '-ac', '1',
        '-ar', sample_rate.to_s,
        '-f', 'f32le',
        'pipe:1'
      ]
    end

    def build_envelope(samples)
      samples.each_slice(samples_per_interval).map do |slice|
        root_mean_square(slice)
      end
    end

    def samples_per_interval
      (interval_seconds * sample_rate).round
    end

    def root_mean_square(samples)
      mean_square = samples.sum do |sample|
        sample**2
      end.fdiv(samples.length)

      Math.sqrt(mean_square)
    end
  end
end
