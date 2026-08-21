# frozen_string_literal: true

module VideoEncoder
  # Builds an MLT project XML document for a given video encoder project.
  class MltProjectBuilder
    def build(
      project,
      video_index: 0, audio_index: 0,
      audio_tracks_by_source: nil, video_tracks_by_source: nil
    )
      sources = project.segments.map(&:source).uniq
      source_ids = sources.each_with_index.to_h do |source, index|
        source_id = index.zero? ? 'source' : "source_#{index}"
        [source, source_id]
      end

      chains = sources.map do |source|
        source_id = source_ids.fetch(source)
        selected_video_index = track_index(
          video_tracks_by_source,
          source,
          video_index
        )

        selected_audio_index = track_index(
          audio_tracks_by_source,
          source,
          audio_index
        )

        <<~CHAIN.chomp
          <chain id="#{source_id}">
            <property name="resource">#{source.path}</property>
            <property name="video_index">#{selected_video_index}</property>
            <property name="audio_index">#{selected_audio_index}</property>
          </chain>
        CHAIN
      end.join("\n")

      entries = project.segments.map do |segment|
        source_id = source_ids.fetch(segment.source)
        start_position, end_position = segment_boundaries(segment)

        <<~XML.strip
          <entry in="#{start_position}" out="#{end_position}" producer="#{source_id}"/>
        XML
      end

      <<~XML
        <mlt>
          <profile colorspace="709"
             description="HD 1080i 25 fps"
             display_aspect_den="9"
             display_aspect_num="16"
             frame_rate_den="1"
             frame_rate_num="25"
             height="1080"
             progressive="0"
             sample_aspect_den="1"
             sample_aspect_num="1"
             width="1920"/>
             #{chains}
          <playlist id="segments">
            #{entries.join("\n    ")}
          </playlist>
        </mlt>
      XML
    end

    private

    def track_index(tracks_by_source, source, default_index)
      return default_index unless tracks_by_source

      tracks_by_source.fetch(source).index
    end

    def segment_boundaries(segment)
      [
        segment.start_frame || segment.start_time,
        segment.end_frame || segment.end_time
      ]
    end
  end
end
