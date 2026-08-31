# frozen_string_literal: true

module VideoEncoder
  # Plans bounded samples for checking selected media tracks.
  class TrackPreflightPlanner
    def initialize(sample_seconds: 60)
      unless sample_seconds.is_a?(Integer) && sample_seconds.positive?
        raise ArgumentError, 'sample_seconds must be a positive integer'
      end

      @sample_seconds = sample_seconds
    end

    def call(
      trim_project:,
      video_tracks_by_source:,
      audio_output_tracks:,
      subtitle_tracks_by_source:,
      confirmed_audio_tracks_by_source: {}
    )
      segments_by_source = trim_project.segments.group_by(&:source)

      segments_by_source.flat_map do |source, segments|
        tracks = selected_tracks(
          source,
          audio_output_tracks,
          subtitle_tracks_by_source,
          confirmed_audio_tracks_by_source.fetch(source, [])
        )

        next [] if tracks.empty?

        frame_rate = video_tracks_by_source.fetch(source).frame_rate
        bounds = sample_bounds(segments, frame_rate)

        tracks.map do |track|
          {
            source: source,
            track: track,
            start_frame: bounds.fetch(:start_frame),
            end_frame: bounds.fetch(:end_frame),
            frame_rate: frame_rate
          }
        end
      end
    end

    private

    attr_reader :sample_seconds

    def selected_tracks(
      source,
      audio_outputs,
      subtitle_tracks,
      confirmed_audio_indexes
    )
      tracks = audio_outputs.map { |output| output.track_for(source) }

      tracks.reject! do |track|
        confirmed_audio_indexes.include?(track.index)
      end

      subtitle = subtitle_tracks[source]
      tracks << subtitle if subtitle

      tracks.uniq(&:index)
    end

    def sample_bounds(segments, frame_rate)
      raise ArgumentError, 'a positive video frame rate is required' unless frame_rate&.positive?

      segment = segments.max_by { |item| frame_count(item) }
      segment_length = frame_count(segment)
      requested_length = [(sample_seconds * frame_rate).floor, 1].max
      sample_length = [requested_length, segment_length].min
      offset = (segment_length - sample_length) / 2
      start_frame = segment.start_frame + offset

      {
        start_frame: start_frame,
        end_frame: start_frame + sample_length - 1
      }
    end

    def frame_count(segment)
      raise ArgumentError, 'preflight samples require frame boundaries' unless segment.start_frame && segment.end_frame

      segment.end_frame - segment.start_frame + 1
    end
  end
end
