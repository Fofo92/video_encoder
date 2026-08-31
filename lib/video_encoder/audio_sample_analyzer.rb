# frozen_string_literal: true

require 'open3'

module VideoEncoder
  # Checks decoded audio signal levels within a selected sample.
  class AudioSampleAnalyzer
    class InvalidMeasurement < StandardError; end

    def initialize(executor: Open3, signal_threshold_db: -60)
      @executor = executor
      @signal_threshold_db = signal_threshold_db
    end

    def call(sample)
      command = build_command(sample)
      _output, diagnostic, status = executor.capture3(*command)

      unless status.success?
        failure = CommandRunner::CommandFailed.new(
          command: command,
          status: status
        )

        raise failure, "#{failure.message}\n#{diagnostic}"
      end

      analyze(diagnostic)
    end

    private

    attr_reader :executor, :signal_threshold_db

    def build_command(sample)
      validate_sample(sample)

      frame_rate = sample.fetch(:frame_rate)
      first = sample.fetch(:start_frame)
      frame_count = sample.fetch(:end_frame) - first + 1

      start_time = Rational(first, 1) / frame_rate
      duration = Rational(frame_count, 1) / frame_rate

      [
        'ffmpeg',
        '-hide_banner',
        '-nostdin',
        '-nostats',
        '-loglevel', 'info',
        '-xerror',
        '-ss', format('%.9f', start_time),
        '-i', sample.fetch(:source).path.to_s,
        '-t', format('%.9f', duration),
        '-map', "0:#{sample.fetch(:track).index}",
        '-vn',
        '-sn',
        '-dn',
        '-af', 'volumedetect',
        '-f', 'null',
        '-'
      ]
    end

    def validate_sample(sample)
      raise ArgumentError, 'an audio track is required' unless sample.fetch(:track).type == :audio
      raise ArgumentError, 'a positive frame rate is required' unless sample.fetch(:frame_rate).positive?

      first = sample.fetch(:start_frame)
      last = sample.fetch(:end_frame)

      unless first.is_a?(Integer) && last.is_a?(Integer) &&
             first >= 0 && last >= first
        raise ArgumentError, 'valid inclusive frame boundaries are required'
      end
    end

    def analyze(diagnostic)
      count = diagnostic.scan(/\bn_samples:\s*(\d+)/).last

      raise InvalidMeasurement, 'missing decoded sample count' unless count

      sample_count = Integer(count.first)

      if sample_count.zero?
        return {
          status: :inconclusive,
          sample_count: 0,
          mean_volume_db: nil,
          max_volume_db: nil
        }
      end

      mean_volume = read_volume(diagnostic, 'mean_volume')
      max_volume = read_volume(diagnostic, 'max_volume')

      {
        status: mean_volume > signal_threshold_db ? :signal_detected : :inconclusive,
        sample_count: sample_count,
        mean_volume_db: mean_volume,
        max_volume_db: max_volume
      }
    end

    def read_volume(diagnostic, name)
      match = diagnostic.scan(
        /\b#{Regexp.escape(name)}:\s*(-inf|[+-]?\d+(?:\.\d+)?)\s+dB/
      ).last

      raise InvalidMeasurement, "missing #{name} measurement" unless match

      value = match.first
      value == '-inf' ? -Float::INFINITY : Float(value)
    end
  end
end
