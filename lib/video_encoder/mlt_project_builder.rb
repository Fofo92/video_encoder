# frozen_string_literal: true

module VideoEncoder
  # Builds an MLT project XML document for a given video encoder project.
  class MltProjectBuilder
    def initialize(profile: VideoExportProfile.hd_720p25)
      @profile = profile
    end

    def build(
      project,
      video_index: 0, audio_index: 0,
      audio_tracks_by_source: nil, video_tracks_by_source: nil
    )
      chains = project.segments.each_with_index.map do |segment, index|
        source = segment.source
        source_id = index.zero? ? 'source' : "source_#{index}"
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

      entries = project.segments.each_with_index.map do |segment, index|
        source_id = index.zero? ? 'source' : "source_#{index}"
        start_position, end_position = segment_boundaries(
          segment,
          video_tracks_by_source
        )

        <<~XML.strip
          <entry in="#{start_position}" out="#{end_position}" producer="#{source_id}"/>
        XML
      end

      <<~XML
        <mlt>
          <profile colorspace="#{@profile.colorspace}"
            display_aspect_den="#{@profile.display_aspect_ratio.denominator}"
            display_aspect_num="#{@profile.display_aspect_ratio.numerator}"
            frame_rate_den="#{@profile.frame_rate.denominator}"
            frame_rate_num="#{@profile.frame_rate.numerator}"
            height="#{@profile.height}"
            progressive="#{@profile.progressive? ? 1 : 0}"
            sample_aspect_den="#{@profile.sample_aspect_ratio.denominator}"
            sample_aspect_num="#{@profile.sample_aspect_ratio.numerator}"
            width="#{@profile.width}"/>
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

    def segment_boundaries(segment, video_tracks_by_source)
      return [segment.start_time, segment.end_time] if segment.start_frame.nil?

      unless video_tracks_by_source
        raise ArgumentError,
              'video_tracks_by_source is required for frame boundaries'
      end

      source_frame_rate = video_tracks_by_source.fetch(segment.source).frame_rate
      output_frame_rate = @profile.frame_rate

      start_position = (
        segment.start_frame * output_frame_rate / source_frame_rate
      ).floor

      exclusive_end_position = (
        (segment.end_frame + 1) * output_frame_rate / source_frame_rate
      ).ceil

      [start_position, exclusive_end_position - 1]
    end
  end
end
