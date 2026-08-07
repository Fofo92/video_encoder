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
        project_path,
        '-consumer',
        "avformat:#{output_path}",
        'vcodec=libx265',
        'an=1'
      )
    end

    def render_audio(project_path:, output_path:)
      runner.run(
        'melt-7',
        project_path,
        '-consumer',
        "avformat:#{output_path}",
        'acodec=flac',
        'vn=1'
      )
    end

    private

    attr_reader :runner
  end
end
