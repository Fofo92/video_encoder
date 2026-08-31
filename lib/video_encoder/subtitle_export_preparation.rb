# frozen_string_literal: true

module VideoEncoder
  # Prepares subtitles and applies the original-audio retention policy.
  class SubtitleExportPreparation
    def initialize(exporter:, progress_reporter:)
      @exporter = exporter
      @progress_reporter = progress_reporter
    end

    def call(
      trim_project:,
      video_tracks_by_source:,
      subtitle_tracks_by_source:,
      audio_output_tracks:
    )
      return [nil, audio_output_tracks] unless exporter

      progress_reporter&.call(
        stage: :subtitles,
        step: 1,
        total: audio_output_tracks.length + 3
      )

      subtitle_path = extract_subtitles(
        trim_project: trim_project,
        video_tracks_by_source: video_tracks_by_source,
        subtitle_tracks_by_source: subtitle_tracks_by_source
      )

      [
        subtitle_path,
        retained_audio_tracks(audio_output_tracks, subtitle_path)
      ]
    end

    private

    attr_reader :exporter, :progress_reporter

    def extract_subtitles(**arguments)
      exporter.call(**arguments)
    rescue TrimSubtitleExporter::IncompleteSubtitles => e
      e.missing_groups.each do |group|
        warn(
          code: 'no_subtitles_found',
          message: "Aucun sous-titre trouvé pour le groupe #{group}.",
          group: group
        )
      end

      raise unless e.subtitle_path.nil?

      nil
    end

    def retained_audio_tracks(audio_tracks, subtitle_path)
      return audio_tracks if subtitle_path

      retained = audio_tracks.reject { |track| track.role == :original }

      return audio_tracks if retained.length == audio_tracks.length

      if retained.empty?
        raise ArgumentError,
              'Aucune piste audio française disponible après exclusion de la piste originale.'
      end

      warn(
        code: 'original_audio_omitted_no_subtitles',
        message: 'Aucun sous-titre exploitable : export sans sous-titres ni piste audio qaa.'
      )

      retained
    end

    def warn(**details)
      return unless progress_reporter.respond_to?(:warning)

      progress_reporter.warning(**details)
    end
  end
end
