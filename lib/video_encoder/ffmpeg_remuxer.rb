# frozen_string_literal: true

module VideoEncoder
  # Combines separately rendered streams into the final media file.
  class FfmpegRemuxer
    LANGUAGE_BY_ROLE = { french: 'fra', original: 'qaa' }.freeze

    def initialize(runner:)
      @runner = runner
    end

    def remux(
      video_path:,
      audio_inputs:,
      output_path:,
      subtitle_path: nil
    )
      command = [
        'ffmpeg',
        '-i', video_path
      ]

      audio_inputs.each do |audio_input|
        command.push('-i', audio_input.fetch(:path))
      end

      command.push('-i', subtitle_path) if subtitle_path
      command.push('-map', '0:v:0')

      audio_inputs.each_with_index do |_audio_input, index|
        command.push('-map', "#{index + 1}:a:0")
      end

      if subtitle_path
        subtitle_input_index = audio_inputs.length + 1
        command.push('-map', "#{subtitle_input_index}:s:0")
      end

      command.push('-c', 'copy')
      command.push('-c:s', 'srt') if subtitle_path

      audio_inputs.each_with_index do |audio_input, index|
        output_track = audio_input.fetch(:output_track)
        language = LANGUAGE_BY_ROLE.fetch(output_track.role)

        command.push(
          "-metadata:s:a:#{index}",
          "language=#{language}"
        )
      end

      if subtitle_path
        command.push(
          '-metadata:s:s:0', 'language=fra',
          '-metadata:s:s:0', 'title=Français'
        )
      end

      command << output_path

      runner.run(*command)
    end

    private

    attr_reader :runner
  end
end
