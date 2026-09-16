# frozen_string_literal: true

require 'open3'

module VideoEncoder
  # Decodes normalized grayscale frames for timeline comparison.
  class VideoFrameSequenceExtractor
    def initialize(
      width:,
      height:,
      frame_rate:,
      seek_preroll_seconds: 0,
      executor: Open3
    )
      @width = width
      @height = height
      @frame_rate = frame_rate
      @seek_preroll_seconds = seek_preroll_seconds
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

      output, diagnostic, status = executor.capture3(
        *command
      )

      unless status.success?
        failure = CommandRunner::CommandFailed.new(
          command: command,
          status: status
        )

        raise failure,
              "#{failure.message}\n#{diagnostic}"
      end

      output
        .unpack('C*')
        .each_slice(frame_size)
        .map(&:itself)
    end

    private

    attr_reader :executor,
                :frame_rate,
                :height,
                :seek_preroll_seconds,
                :width

    def command(
      path:,
      stream_index:,
      start_seconds:,
      duration_seconds:
    )
      preroll = [
        seek_preroll_seconds,
        start_seconds
      ].min

      input_start = start_seconds - preroll

      arguments = [
        'ffmpeg',
        '-hide_banner',
        '-nostdin',
        '-loglevel', 'error',
        '-ss', format('%.6f', input_start),
        '-i', path.to_s
      ]

      if preroll.positive?
        arguments.push(
          '-ss',
          format('%.6f', preroll)
        )
      end

      arguments.push(
        '-t', format('%.6f', duration_seconds),
        '-map', "0:#{stream_index}",
        '-an',
        '-sn',
        '-dn',
        '-vf', video_filter,
        '-f', 'rawvideo',
        'pipe:1'
      )
    end

    def video_filter
      [
        "scale=#{width}:#{height}",
        'format=gray',
        "fps=#{frame_rate}"
      ].join(',')
    end

    def frame_size
      width * height
    end
  end
end
