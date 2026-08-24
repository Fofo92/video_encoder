# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::FfmpegSubtitleSegmentExtractor do
  subject(:extractor) { described_class.new(runner: runner) }

  let(:runner) { instance_double('CommandRunner') }

  describe '#call' do
    it 'extracts a clocked subtitle segment with trailing padding' do
      video_track = instance_double(
        VideoEncoder::VideoTrack,
        index: 0
      )

      subtitle_track = instance_double(
        VideoEncoder::Track,
        index: 5
      )

      allow(runner).to receive(:run)

      extractor.call(
        source_path: '/media/movie.m2t',
        video_track: video_track,
        subtitle_track: subtitle_track,
        start_time: 1_200,
        duration: 60,
        output_path: '/tmp/subtitle_segment.ts'
      )

      expect(runner).to have_received(:run).with(
        'ffmpeg',
        '-y',
        '-loglevel', 'warning',
        '-i', '/media/movie.m2t',
        '-ss', '1200',
        '-t', '62',
        '-map', '0:0',
        '-map', '0:5',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '30',
        '-c:s', 'copy',
        '-muxdelay', '0',
        '-muxpreload', '0',
        '-f', 'mpegts',
        '/tmp/subtitle_segment.ts'
      )
    end
  end
end
