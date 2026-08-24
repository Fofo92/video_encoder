# frozen_string_literal: true

module VideoEncoder
  # Extracts and OCRs one continuous subtitle project timeline.
  class SubtitleProjectProcessor
    def initialize(
      extractor:,
      concatenator:,
      ocr:,
      normalizer:,
      reader:,
      synchronization_delay:
    )
      @extractor = extractor
      @concatenator = concatenator
      @ocr = ocr
      @normalizer = normalizer
      @reader = reader
      @synchronization_delay = synchronization_delay
    end

    def call(
      segments:,
      timeline_start:,
      manifest_path:,
      transport_path:,
      srt_path:
    )
      transports = segments.map do |item|
        extract_segment(item)
      end

      concatenator.call(
        segments: transports,
        manifest_path: manifest_path,
        output_path: transport_path
      )

      ocr.call(
        input_path: transport_path,
        output_path: srt_path
      )

      duration = transports.sum do |transport|
        transport.fetch(:duration)
      end

      normalizer.call(
        reader.read(srt_path),
        offset: timeline_start + synchronization_delay,
        start_at: timeline_start,
        end_at: timeline_start + duration
      )
    end

    private

    attr_reader :extractor,
                :concatenator,
                :ocr,
                :normalizer,
                :reader,
                :synchronization_delay

    def extract_segment(item)
      segment = item.fetch(:segment)
      video_track = item.fetch(:video_track)
      duration = segment_duration(segment, video_track)
      transport_path = item.fetch(:transport_path)

      extractor.call(
        source_path: segment.source.path,
        video_track: video_track,
        subtitle_track: item.fetch(:subtitle_track),
        start_time: segment_start_time(segment, video_track),
        duration: duration,
        output_path: transport_path
      )

      {
        path: transport_path,
        duration: duration
      }
    end

    def segment_start_time(segment, video_track)
      Rational(segment.start_frame, 1) / video_track.frame_rate
    end

    def segment_duration(segment, video_track)
      frame_count = segment.end_frame - segment.start_frame + 1

      Rational(frame_count, 1) / video_track.frame_rate
    end
  end
end
