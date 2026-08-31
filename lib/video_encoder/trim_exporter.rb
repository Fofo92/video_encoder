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
      progress_reporter: nil
    )
      @builder = builder
      @renderer = renderer
      @remuxer = remuxer
      @workspace = workspace
      @subtitle_exporter = subtitle_exporter
      @progress_reporter = progress_reporter
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

      subtitle_path, selected_audio_tracks = SubtitleExportPreparation.new(
        exporter: subtitle_exporter,
        progress_reporter: progress_reporter
      ).call(
        trim_project: trim_project,
        video_tracks_by_source: video_tracks_by_source,
        subtitle_tracks_by_source: subtitle_tracks_by_source,
        audio_output_tracks: selected_audio_tracks
      )

      total_steps = total_steps_for(selected_audio_tracks)

      render_video(
        trim_project,
        video_tracks_by_source,
        total_steps
      )

      audio_inputs = render_audio_tracks(
        trim_project,
        sources,
        selected_audio_tracks,
        video_tracks_by_source,
        total_steps
      )

      report_progress(:remux, step: total_steps, total: total_steps)

      args = {
        video_path: workspace.video_path,
        audio_inputs: audio_inputs,
        output_path: output_path
      }
      args[:subtitle_path] = subtitle_path if subtitle_path

      @remuxer.remux(**args)
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
        step: subtitle_exporter ? 2 : 1,
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
      audio_tracks.each_with_index.map do |output_track, index|
        render_audio_track(
          trim_project,
          sources,
          output_track,
          video_tracks_by_source,
          index,
          audio_tracks.length,
          total_steps
        )
      end
    end

    def render_audio_track(
      trim_project,
      sources,
      output_track,
      video_tracks_by_source,
      index,
      track_count,
      total_steps
    )
      report_progress(
        :audio,
        step: index + (subtitle_exporter ? 3 : 2),
        total: total_steps,
        track: index + 1,
        tracks: track_count,
        role: output_track.role
      )

      tracks_by_source = sources.to_h do |source|
        [source, output_track.track_for(source)]
      end

      audio_xml = builder.build(
        trim_project,
        video_index: -1,
        audio_tracks_by_source: tracks_by_source,
        video_tracks_by_source: video_tracks_by_source
      )

      workspace.write_mlt(audio_xml)

      audio_path = workspace.audio_path(output_track)

      renderer.render_audio(
        project_path: workspace.mlt_path,
        output_path: audio_path
      )

      {
        path: audio_path,
        output_track: output_track
      }
    end

    def report_progress(stage, **details)
      progress_reporter&.call(stage: stage, **details)
    end
  end
end
