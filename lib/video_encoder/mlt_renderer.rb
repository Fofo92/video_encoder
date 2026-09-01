# frozen_string_literal: true

module VideoEncoder
  # Renders elementary media streams from an MLT project.
  class MltRenderer
    def initialize(runner:)
      @runner = runner
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
    end

    def render_audio(project_path:, output_path:)
      runner.run(
        'melt-7',
        '-progress2',
        project_path,
        '-consumer',
        "avformat:#{output_path}",
        'acodec=aac',
        'ab=160k',
        'vn=1'
      )
    end

    private

    attr_reader :runner
  end
end
