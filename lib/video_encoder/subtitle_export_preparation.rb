# frozen_string_literal: true

module VideoEncoder
  # Prepares subtitles and applies the original-audio retention policy.
  class SubtitleExportPreparation
    class RequiredSubtitlesUnavailable < StandardError; end

    def self.skip?(trim_project, subtitle_tracks_by_source)
      selection = trim_project.track_selection if trim_project.respond_to?(:track_selection)
      modes = %w[french_only original_without_subtitles french_with_burned_subtitles]
      selection.is_a?(Hash) && modes.include?(selection['mode']) && subtitle_tracks_by_source.empty?
    end

    def initialize(exporter:, progress_reporter:)
      @exporter = exporter
      @progress_reporter = progress_reporter
    end

    def call(
      trim_project:,
      video_tracks_by_source:,
      subtitle_tracks_by_source:,
      audio_output_tracks:,
      rendered_video_path:
    )
      if absent_subtitles?(trim_project, video_tracks_by_source, subtitle_tracks_by_source)
        warn_missing_tracks
        return [nil, audio_output_tracks]
      end

      unless exporter
        require_subtitles!(trim_project)
        return [nil, audio_output_tracks]
      end
      return [nil, audio_output_tracks] if self.class.skip?(trim_project, subtitle_tracks_by_source)

      progress_reporter&.call(
        stage: :subtitles,
        step: 2,
        total: audio_output_tracks.length + 3
      )

      subtitle_path = extract_subtitles(
        trim_project: trim_project,
        video_tracks_by_source: video_tracks_by_source,
        subtitle_tracks_by_source: subtitle_tracks_by_source,
        rendered_video_path: rendered_video_path
      )

      [
        subtitle_path,
        retained_audio_tracks(audio_output_tracks, subtitle_path, trim_project)
      ]
    end

    private

    attr_reader :exporter, :progress_reporter

    def absent_subtitles?(project, video_tracks, subtitle_tracks)
      return false unless vmst?(project) && subtitle_tracks.empty?

      sources = video_tracks.keys
      sources.any? && sources.all? { |source| source.subtitle_tracks.empty? }
    end

    def warn_missing_tracks
      warn(
        code: 'vmst_without_subtitle_tracks',
        message: 'VMST demandée, mais aucune piste de sous-titres présente dans les sources utilisées. ' \
                 'Les pistes audio sélectionnées sont conservées : export sans sous-titres.'
      )
    end

    def vmst?(project)
      selection = project.track_selection if project.respond_to?(:track_selection)
      selection&.fetch('mode', nil) == 'original_with_subtitles'
    end

    def extract_subtitles(**arguments)
      export_subtitles(**arguments)
    rescue CcextractorOcr::TechnicalFailure
      fallback_tracks = hearing_impaired_fallback(
        arguments.fetch(:subtitle_tracks_by_source)
      )

      raise unless fallback_tracks

      warn(
        code: 'hearing_impaired_subtitles_fallback',
        message: 'La piste de sous-titres normale est inutilisable : utilisation de la piste pour malentendants.'
      )

      export_subtitles(
        **arguments,
        subtitle_tracks_by_source: fallback_tracks
      )
    end

    def export_subtitles(**arguments)
      exporter.call(**arguments)
    rescue TrimSubtitleExporter::IncompleteSubtitles => e
      return unless e.subtitle_path

      e.missing_groups.each do |group|
        warn(
          code: 'no_subtitles_found',
          message: "Aucun sous-titre trouvé pour le groupe #{group}.",
          group: group
        )
      end

      raise
    end

    def hearing_impaired_fallback(tracks_by_source)
      replacement_found = false

      fallback_tracks = tracks_by_source.to_h do |source, selected|
        replacement = source.subtitle_tracks.find do |candidate|
          candidate.index != selected.index &&
            candidate.language == selected.language &&
            candidate.hearing_impaired
        end

        replacement_found = true if replacement

        [source, replacement || selected]
      end

      fallback_tracks if replacement_found
    end

    def retained_audio_tracks(audio_tracks, subtitle_path, project)
      return audio_tracks if preserve_audio?(project, subtitle_path)

      retained = audio_tracks.reject { |track| track.role == :original }

      return audio_tracks if retained.length == audio_tracks.length

      if retained.empty?
        raise ArgumentError,
              'Aucune piste audio française disponible après exclusion de la piste originale.'
      end

      warn(
        code: 'original_audio_omitted_no_subtitles',
        message:
          'Aucun sous-titre exploitable n’a été trouvé. ' \
          'L’export se poursuit sans sous-titres ni piste audio ' \
          'en version originale.'
      )

      retained
    end

    def preserve_audio?(project, subtitle_path)
      selection = project.track_selection if project.respond_to?(:track_selection)
      return true if selection&.fetch('mode', nil) == 'original_without_subtitles'
      return true if subtitle_path
      return false unless vmst?(project)

      warn(
        code: 'vmst_without_subtitle_text',
        message: 'VMST demandée, mais aucun texte de sous-titres exploitable obtenu. ' \
                 'Les pistes audio sélectionnées sont conservées : export en VM, sans sous-titres.'
      )
      true
    end

    def require_subtitles!(project)
      return unless vmst?(project)

      raise RequiredSubtitlesUnavailable,
            'VMST demandée mais exporteur de sous-titres absent : vérifier la configuration.'
    end

    def warn(**details)
      return unless progress_reporter.respond_to?(:warning)

      progress_reporter.warning(**details)
    end
  end
end
