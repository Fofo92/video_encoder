# frozen_string_literal: true

module VideoEncoder
  # Concatenates clocked subtitle transports on the project timeline.
  class FfmpegSubtitleProjectConcatenator
    def initialize(runner:, writer:)
      @runner = runner
      @writer = writer
    end

    def call(segments:, manifest_path:, output_path:)
      writer.write(
        manifest_path,
        build_manifest(segments)
      )

      runner.run(
        'ffmpeg',
        '-y',
        '-loglevel', 'warning',
        '-f', 'concat',
        '-safe', '0',
        '-i', manifest_path,
        '-map', '0:v:0',
        '-map', '0:s:0',
        '-c', 'copy',
        '-muxdelay', '0',
        '-muxpreload', '0',
        '-f', 'mpegts',
        output_path
      )
    end

    private

    attr_reader :runner, :writer

    def build_manifest(segments)
      lines = ['ffconcat version 1.0']

      segments.each do |segment|
        duration = format_time(segment.fetch(:duration))

        lines.push(
          "file #{quote_path(segment.fetch(:path))}",
          'inpoint 0',
          "outpoint #{duration}",
          "duration #{duration}"
        )
      end

      "#{lines.join("\n")}\n"
    end

    def quote_path(path)
      escaped = path.to_s.gsub("'") do
        "'\\''"
      end

      "'#{escaped}'"
    end

    def format_time(value)
      return value.to_i.to_s if value.to_i == value

      value.to_f.to_s
    end
  end
end
