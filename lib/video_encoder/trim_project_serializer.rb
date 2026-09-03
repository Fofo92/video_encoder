# frozen_string_literal: true

require 'json'
require 'time'

module VideoEncoder
  # Serializes a trim project into its versioned JSON representation.
  class TrimProjectSerializer
    def dump(project)
      sources = project_sources(project)
      source_ids = build_source_ids(sources)

      JSON.generate(
        format: TrimProjectDocument::FORMAT,
        version: TrimProjectDocument::VERSION,
        sources: sources.map do |source|
          serialize_source(
            source,
            source_ids.fetch(source)
          )
        end,
        timeline: project.timeline.map do |item|
          serialize(item, source_ids)
        end
      )
    end

    private

    def project_sources(project)
      project.timeline.filter_map do |item|
        item.source if item.is_a?(Segment)
      end.uniq
    end

    def build_source_ids(sources)
      sources.each_with_index.to_h do |source, index|
        identifier = (
          index.zero? ? 'source' : "source_#{index}"
        )

        [source, identifier]
      end
    end

    def serialize_source(source, identifier)
      {
        id: identifier,
        path: source.path.to_s,
        inspection: serialize_inspection(source)
      }
    end

    def serialize_inspection(source)
      inspection = {
        duration: source.duration
      }

      inspection[:inspected_at] = source.inspected_at.iso8601 if source.inspected_at

      inspection[:size_bytes] = source.size_bytes if source.size_bytes

      return inspection if source.tracks.empty?

      inspection.merge(
        video_tracks: source.video_tracks.map do |track|
          serialize_video_track(track)
        end,
        audio_tracks: source.audio_tracks.map do |track|
          serialize_audio_track(track)
        end,
        subtitle_tracks: source.subtitle_tracks.map do |track|
          serialize_subtitle_track(track)
        end
      )
    end

    def serialize_video_track(track)
      {
        index: track.index,
        codec: track.codec,
        width: track.width,
        height: track.height,
        frame_rate: serialize_frame_rate(
          track.frame_rate
        )
      }
    end

    def serialize_audio_track(track)
      {
        index: track.index,
        codec: track.codec,
        language: track.language,
        default: track.default,
        visual_impaired: track.visual_impaired
      }
    end

    def serialize_subtitle_track(track)
      {
        index: track.index,
        codec: track.codec,
        language: track.language,
        default: track.default,
        forced: track.forced,
        hearing_impaired: track.hearing_impaired
      }
    end

    def serialize_frame_rate(frame_rate)
      return unless frame_rate

      {
        numerator: frame_rate.numerator,
        denominator: frame_rate.denominator
      }
    end

    def serialize(item, source_ids)
      case item
      when Segment
        serialize_segment(item, source_ids)
      when Gap
        {
          type: 'gap',
          frame_count: item.frame_count
        }
      else
        raise ArgumentError,
              "unsupported timeline item: #{item.class}"
      end
    end

    def serialize_segment(segment, source_ids)
      unless segment.start_frame && segment.end_frame
        raise ArgumentError,
              'persistent segments require frame boundaries'
      end

      {
        type: 'segment',
        source_id: source_ids.fetch(segment.source),
        start_frame: segment.start_frame,
        end_frame: segment.end_frame
      }
    end
  end
end
