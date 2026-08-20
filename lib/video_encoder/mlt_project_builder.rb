# frozen_string_literal: true

module VideoEncoder
  # Builds an MLT project XML document for a given video encoder project.
  class MltProjectBuilder
    def build(project, video_index: 0, audio_index: 0)
      entries = project.segments.map do |segment|
        <<~XML.strip
          <entry in="#{segment.start_time}" out="#{segment.end_time}" producer="source"/>
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
          <chain id="source">
            <property name="resource">#{project.segments.first.source.path}</property>
            <property name="video_index">#{video_index}</property>
            <property name="audio_index">#{audio_index}</property>
          </chain>
          <playlist id="segments">
            #{entries.join("\n    ")}
          </playlist>
        </mlt>
      XML
    end
  end
end
