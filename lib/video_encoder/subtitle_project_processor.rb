# frozen_string_literal: true

module VideoEncoder
  # Extracts and OCRs one continuous subtitle project timeline.
  class SubtitleProjectProcessor
    def initialize(
      extractor:,
      concatenator:,
      ocr:,
      ocr_timing_correction:,
      synchronization_probe:,
      timeline_normalizer:,
      reader:,
      synchronization_delay:
    )
      @extractor = extractor
      @concatenator = concatenator
      @ocr = ocr
      @ocr_timing_correction = ocr_timing_correction
      @synchronization_probe = synchronization_probe
      @timeline_normalizer = timeline_normalizer
      @reader = reader
      @synchronization_delay = synchronization_delay
    end

    def call(
      segments:,
      timeline_start:,
      rendered_video_path:,
      manifest_path:,
      transport_path:,
      srt_path:
    )
      transports = segments.map do |item|
        extract_segment(item)
      end

      corrections = measure_corrections(
        segments,
        transports,
        timeline_start,
        rendered_video_path
      )

      concatenator.call(
        segments: transports,
        manifest_path: manifest_path,
        output_path: transport_path
      )

      ocr.call(
        input_path: transport_path,
        output_path: srt_path
      )

      raw_srt = reader.read(srt_path)

      corrections = corrections.map do |correction|
        correction.merge(
          offset_seconds:
            ocr_timing_correction.call(
              srt: raw_srt,
              transport_path: transport_path,
              alignment_offset:
                correction.fetch(:offset_seconds)
            ) +
              synchronization_delay
        )
      end

      timeline_normalizer.call(
        raw_srt,
        timeline_start: timeline_start,
        segments: corrections
      )
    end

    private

    attr_reader :extractor,
                :concatenator,
                :ocr,
                :reader,
                :synchronization_delay,
                :synchronization_probe,
                :timeline_normalizer,
                :ocr_timing_correction

    def extract_segment(item)
      segment = item.fetch(:segment)
      video_track = item.fetch(:video_track)
      duration = segment_duration(
        segment,
        video_track
      )

      transport_path = item.fetch(
        :transport_path
      )

      extractor.call(
        source_path: segment.source.path,
        video_track: video_track,
        subtitle_track:
          item.fetch(:subtitle_track),
        start_time:
          segment_start_time(
            segment,
            video_track
          ),
        duration: duration,
        output_path: transport_path
      )

      {
        path: transport_path,
        duration: duration
      }
    end

    def measure_corrections(
      segments,
      transports,
      timeline_start,
      rendered_video_path
    )
      rendered_start = timeline_start

      segments.zip(transports).map do |item, transport|
        correction = measure_correction(
          item,
          transport,
          rendered_video_path,
          rendered_start
        )

        rendered_start += transport.fetch(
          :duration
        )

        {
          duration: transport.fetch(:duration),
          offset_seconds:
            correction.fetch(:offset_seconds)
        }
      end
    end

    def measure_correction(
      item,
      transport,
      rendered_video_path,
      rendered_start
    )
      segment = item.fetch(:segment)
      video_track = item.fetch(:video_track)

      synchronization_probe.call(
        source_path: segment.source.path,
        source_stream_index:
          video_track.index,
        source_start_seconds:
          segment_start_time(
            segment,
            video_track
          ),
        duration_seconds:
            transport.fetch(:duration),
        transport_path:
          transport.fetch(:path),
        rendered_video_path:
          rendered_video_path,
        rendered_start_seconds:
          rendered_start
      )
    end

    def segment_start_time(segment, video_track)
      Rational(segment.start_frame, 1) /
        video_track.frame_rate
    end

    def segment_duration(segment, video_track)
      frame_count = (
        segment.end_frame -
        segment.start_frame +
        1
      )

      Rational(frame_count, 1) /
        video_track.frame_rate
    end
  end
end
