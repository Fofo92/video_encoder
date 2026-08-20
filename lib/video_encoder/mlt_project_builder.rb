# frozen_string_literal: true

module VideoEncoder
  # Builds an MLT project XML document for a given video encoder project.
  class MltProjectBuilder
    def build(
      project,
      video_index: 0,
      audio_index: 0,
      audio_tracks_by_source: nil
    )
      sources = project.segments.map(&:source).uniq
      source_ids = sources.each_with_index.to_h do |source, index|
        source_id = index.zero? ? 'source' : "source_#{index}"

        [source, source_id]
      end

      chains = sources.map do |source|
        source_id = source_ids.fetch(source)
        selected_audio_index =
          if audio_tracks_by_source
            audio_tracks_by_source.fetch(source).index
          else
            audio_index
          end

        <<~CHAIN.chomp
          <chain id="#{source_id}">
            <property name="resource">#{source.path}</property>
            <property name="video_index">#{video_index}</property>
            <property name="audio_index">#{selected_audio_index}</property>
          </chain>
        CHAIN
      end.join("\n")

      entries = project.segments.map do |segment|
        source_id = source_ids.fetch(segment.source)

        <<~XML.strip
          <entry in="#{segment.start_time}" out="#{segment.end_time}" producer="#{source_id}"/>
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
  end
end
