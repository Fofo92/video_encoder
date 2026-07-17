# frozen_string_literal: true

require 'open3'

module VideoEncoder
  module Encoder
    # FFmpegEncoder encodes video files using ffmpeg.
    class FFmpegEncoder < Base
      def initialize(logger:, config:, selector:, media_probe:, runner: nil, monitor_factory: nil)
        super(logger: logger)
        @config = config
        @runner = runner || FFmpegRunner.new(logger: logger)
        @selector = selector
        @media_probe = media_probe
        @monitor_factory = monitor_factory || VideoEncoder::EncodingMonitorFactory
      end

      def encode(job)
        source = job.source.to_s

        media = @media_probe.read(source)
        selection = @selector.select(media)

        output = source.sub(/\.[^.]+$/, ".#{@config.container}")

        cmd = [
          'ffmpeg',
          '-y',
          '-progress', 'pipe:1',
          '-nostats',
          '-i', source,
        ]

        cmd = add_maps(cmd, selection)

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
      end

      private

      def add_maps(cmd, selection)
        cmd += ['-map', "0:#{selection[:video].index}"]

        selection[:audio].each do |track|
          cmd += ['-map', "0:#{track.index}"]
        end

        selection[:subtitles].each do |track|
          cmd += ['-map', "0:#{track.index}"]
        end

        cmd
      end
    end
  end
end
