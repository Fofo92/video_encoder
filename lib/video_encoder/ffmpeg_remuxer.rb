# frozen_string_literal: true

module VideoEncoder
  # Combines separately rendered streams into the final media file.
  class FfmpegRemuxer
    LANGUAGE_BY_ROLE = {
      french: 'fra',
      original: 'qaa'
    }.freeze

    def initialize(runner:)
      @runner = runner
    end

    def remux(video_path:, audio_inputs:, output_path:)
      command = [
        'ffmpeg',
        '-i', video_path
      ]

      audio_inputs.each do |audio_input|
        command.push('-i', audio_input.fetch(:path))
      end

      command.push('-map', '0:v:0')

      audio_inputs.each_with_index do |_audio_input, index|
        command.push('-map', "#{index + 1}:a:0")
      end

      command.push('-c', 'copy')

      audio_inputs.each_with_index do |audio_input, index|
        output_track = audio_input.fetch(:output_track)
        language = LANGUAGE_BY_ROLE.fetch(output_track.role)

        command.push(
          "-metadata:s:a:#{index}",
          "language=#{language}"
        )
      end

      command << output_path

      runner.run(*command)
    end

    private

    attr_reader :runner
  end
end
