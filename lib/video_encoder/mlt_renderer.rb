# frozen_string_literal: true

module VideoEncoder
  # Renders elementary media streams from an MLT project.
  class MltRenderer
    class RenderFailed < StandardError; end

    def initialize(runner:, parallel_runner: ParallelCommandRunner.new)
      @runner = runner
      @parallel_runner = parallel_runner
    end

    def render_video(project_path:, output_path:)
      runner.run(
        'melt-7',
        '-progress2',
        project_path,
        '-consumer',
        "avformat:#{output_path}",
        'vcodec=libx265',
        'crf=24',
        'preset=medium',
        'an=1'
      )

      validate_output!(output_path)
    end

    def render_audio(project_path:, output_path:)
      runner.run(*audio_command(project_path, output_path))

      validate_output!(output_path)
    end

    def render_audio_batch(inputs)
      commands = inputs.map do |input|
        {
          argv: audio_command(input.fetch(:project_path), input.fetch(:output_path)),
          log_path: "#{input.fetch(:output_path)}.log"
        }
      end
      @parallel_runner.run(commands, limit: 2)
      inputs.each { |input| validate_output!(input.fetch(:output_path)) }
    end

    private

    attr_reader :runner

    def audio_command(project_path, output_path)
      [
        'melt-7',
        '-progress2',
        project_path,
        '-consumer',
        "avformat:#{output_path}",
        'acodec=aac',
        'ab=160k',
        'vn=1'
      ]
    end

    def validate_output!(output_path)
      return if File.file?(output_path) && !File.empty?(output_path)

      raise RenderFailed,
            "melt did not create output: #{output_path}"
    end
  end
end
