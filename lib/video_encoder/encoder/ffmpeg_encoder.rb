# frozen_string_literal: true

require 'open3'

module VideoEncoder
  module Encoder
    # FFmpegEncoder encodes video files using ffmpeg.
    class FFmpegEncoder < Base
      def initialize(logger:, config:, runner: nil)
        super(logger: logger)
        @config = config
        @runner = runner || FFmpegRunner.new(logger: logger)
      end

      def encode(job)
        source = job.source.to_s

        output = source.sub(/\.[^.]+$/, ".#{@config.container}")

        cmd = [
          'ffmpeg',
          '-y',
          '-progress', 'pipe:1',
          '-nostats',
          '-i', source
        ]

        cmd += ['-vf', 'bwdif'] if @config.deinterlace

        cmd += [
          '-c:v', @config.video_codec,
          '-preset', @config.preset,
          '-tune', @config.tune,
          '-rc', @config.rc,
          '-cq', @config.cq.to_s
        ]

        if @config.spatial_aq
          cmd += [
            '-spatial_aq', '1',
            '-aq-strength', @config.aq_strength.to_s
          ]
        end

        cmd += [
          '-b_ref_mode', @config.b_ref_mode,
          '-c:a', @config.audio_codec,
          output
        ]

        @logger.info(cmd.join(' '))
        @runner.run(cmd)

        output
        # @logger.error(stderr) unless stderr.empty?

        # return output if status.success?

        # message = stderr.lines.reject(&:empty?).last&.strip
        # message ||= "ffmpeg failed (exit #{status.exitstatus})"

        # raise "#{message} (exit #{status.exitstatus})"
      end
    end
  end
end
