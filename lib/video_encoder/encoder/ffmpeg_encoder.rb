# frozen_string_literal: true

require 'open3'

module VideoEncoder
  module Encoder
    # FFmpegEncoder encodes video files using ffmpeg.
    class FFmpegEncoder < Base
      def initialize(logger:, config:, runner: nil, monitor_factory: nil)
        super(logger: logger)
        @config = config
        @runner = runner || FFmpegRunner.new(logger: logger)
        @monitor_factory = monitor_factory || VideoEncoder::EncodingMonitorFactory
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

        filters = []

        filters << 'bwdif' if @config.deinterlace
        filters << 'scale=w=1280:h=720:force_original_aspect_ratio=decrease'

        cmd += ['-vf', filters.join(',')] unless filters.empty?

        cmd += [
          '-c:v', @config.video_codec,
          '-preset', @config.preset,
          '-tune', @config.tune,
          '-rc', 'vbr',
          '-cq', '30',
          '-b:v', '0',
          '-maxrate', '3M',
          '-bufsize', '6M'
        ]

        if @config.spatial_aq
          cmd += [
            '-spatial_aq', '1',
            '-aq-strength', @config.aq_strength.to_s
          ]
        end

        cmd += [
          '-b_ref_mode', @config.b_ref_mode,

          '-c:a', 'aac',
          '-b:a', '160k',
          '-ac', '2',

          '-disposition:v:0', 'default',
          '-disposition:a:0', 'default',

          output
        ]

        @logger.info(cmd.join(' '))

        monitor = @monitor_factory.build(source)
        begin
          @runner.run(cmd) do |stream, line|
            monitor.call(stream, line)
          end
        ensure
          monitor.finish
        end

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
