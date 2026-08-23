# frozen_string_literal: true

module VideoEncoder
  # Extracts, OCRs and normalizes subtitles for one project segment.
  class SubtitleSegmentProcessor
    def initialize(
      extractor:,
      ocr:,
      normalizer:,
      reader:,
      synchronization_delay:
    )
      @extractor = extractor
      @ocr = ocr
      @normalizer = normalizer
      @reader = reader
      @synchronization_delay = synchronization_delay
    end

    def call(
      segment:,
      video_track:,
      subtitle_track:,
      timeline_start:,
      transport_path:,
      srt_path:
    )
      frame_rate = video_track.frame_rate
      start_time = Rational(segment.start_frame, 1) / frame_rate
      frame_count = segment.end_frame - segment.start_frame + 1
      duration = Rational(frame_count, 1) / frame_rate

      extractor.call(
        source_path: segment.source.path,
        video_track: video_track,
        subtitle_track: subtitle_track,
        start_time: start_time,
        duration: duration,
        output_path: transport_path
      )

      ocr.call(
        input_path: transport_path,
        output_path: srt_path
      )

      normalizer.call(
        reader.read(srt_path),
        offset: timeline_start + synchronization_delay,
        end_at: timeline_start + duration
      )
    end

    private

    attr_reader :extractor,
                :ocr,
                :normalizer,
                :reader,
                :synchronization_delay
  end
end
