# frozen_string_literal: true

module VideoEncoder
  # Orchestrates the production of a trimmed media file.
  class TrimExporter
    def initialize(
      builder:,
      renderer:,
      remuxer:,
      workspace:,
      subtitle_exporter: nil,
      progress_reporter: nil,
      audio_concurrency: 2,
      timings: nil
    )
      @builder = builder
      @renderer = renderer
      @remuxer = remuxer
      @workspace = workspace
      @subtitle_exporter = subtitle_exporter
      @progress_reporter = progress_reporter
      @audio_concurrency = audio_concurrency
      @timings = timings
      raise ArgumentError, 'audio concurrency must be 1 or 2' unless [1, 2].include?(audio_concurrency)
    end

    def call(
      trim_project:,
      video_tracks_by_source:,
      audio_output_tracks:,
      output_path:,
      subtitle_tracks_by_source: {}
    )
      sources = trim_project.segments.map(&:source).uniq

      selected_audio_tracks = audio_output_tracks.select do |output_track|
        output_track.complete_for?(sources)
      end

      total_steps = total_steps_for(
        selected_audio_tracks
      )

      measure(:video) do
        render_video(trim_project, video_tracks_by_source, total_steps)
      end

      subtitle_path, selected_audio_tracks = measure(:subtitles) do
        SubtitleExportPreparation.new(
          exporter: subtitle_exporter,
          progress_reporter: progress_reporter
        ).call(
          trim_project: trim_project,
          video_tracks_by_source: video_tracks_by_source,
          subtitle_tracks_by_source: subtitle_tracks_by_source,
          audio_output_tracks: selected_audio_tracks,
          rendered_video_path: workspace.video_path
        )
      end

      audio_inputs = measure(
        :audio, concurrency: [@audio_concurrency, selected_audio_tracks.length].min,
                roles: selected_audio_tracks.map(&:role)
      ) do
        render_audio_tracks(
          trim_project, sources, selected_audio_tracks, video_tracks_by_source, total_steps
        )
      end

      report_progress(:remux, step: total_steps, total: total_steps)

      args = {
        video_path: workspace.video_path,
        audio_inputs: audio_inputs,
        output_path: output_path
      }
      args[:subtitle_path] = subtitle_path if subtitle_path
      measure(:remux) { @remuxer.remux(**args) }
    end

    private

    attr_reader :builder,
                :renderer,
                :remuxer,
                :workspace,
                :subtitle_exporter,
                :progress_reporter

    def total_steps_for(audio_tracks)
      subtitle_steps = subtitle_exporter ? 1 : 0

      audio_tracks.length + subtitle_steps + 2
    end

    def render_video(trim_project, video_tracks_by_source, total_steps)
      report_progress(
        :video,
        step: 1,
        total: total_steps
      )

      video_xml = builder.build(
        trim_project,
        audio_index: -1,
        video_tracks_by_source: video_tracks_by_source
      )

      workspace.write_mlt(video_xml)

      renderer.render_video(
        project_path: workspace.mlt_path,
        output_path: workspace.video_path
      )
    end

    def render_audio_tracks(
      trim_project,
      sources,
      audio_tracks,
      video_tracks_by_source,
      total_steps
    )
      inputs = audio_tracks.map do |output_track|
        prepare_audio_track(trim_project, sources, output_track, video_tracks_by_source)
      end

      render_prepared_audio(inputs, total_steps)
      inputs.map { |input| input.except(:render) }
    end

    def render_prepared_audio(inputs, total_steps)
      if inputs.length > 1 && @audio_concurrency == 2
        report_progress(
          :audio, step: subtitle_exporter ? 3 : 2, total: total_steps,
                  tracks: inputs.length, parallel: true
        )
        renderer.render_audio_batch(inputs.map { |input| input.fetch(:render) })
      else
        render_sequential_audio(inputs, total_steps)
      end
    end

    def render_sequential_audio(inputs, total_steps)
      inputs.each_with_index do |input, index|
        report_progress(
          :audio, step: index + (subtitle_exporter ? 3 : 2), total: total_steps,
                  track: index + 1, tracks: inputs.length, role: input.fetch(:output_track).role
        )
        renderer.render_audio(**input.fetch(:render))
      end
    end

    def prepare_audio_track(trim_project, sources, output_track, video_tracks_by_source)
      tracks_by_source = sources.to_h do |source|
        [source, output_track.track_for(source)]
      end
      audio_xml = builder.build(
        trim_project,
        video_index: -1,
        audio_tracks_by_source: tracks_by_source,
        video_tracks_by_source: video_tracks_by_source
      )
      project_path = workspace.write_audio_mlt(audio_xml, output_track)
      audio_path = workspace.audio_path(output_track)
      {
        path: audio_path, output_track: output_track,
        render: { project_path: project_path, output_path: audio_path }
      }
    end

    def measure(stage, **details, &)
      return yield unless @timings

      @timings.measure(stage, **details, &)
    end

    def report_progress(stage, **details)
      progress_reporter&.call(stage: stage, **details)
    end
  end
end
