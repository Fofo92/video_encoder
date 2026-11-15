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
        '-ss', '1200',
        '-i', '/media/movie.m2t',
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

    it 'seeks to a fractional frame position before opening the DVB input' do
      command = nil
      allow(runner).to receive(:run) { |*arguments| command = arguments }

      extractor.call(
        source_path: '/media/capture.m2t',
        video_track: instance_double(VideoEncoder::VideoTrack, index: 0),
        subtitle_track: instance_double(VideoEncoder::Track, index: 5),
        start_time: Rational(101_095, 25),
        duration: Rational(82_396, 25),
        output_path: '/tmp/subtitle_segment.ts'
      )

      seek = command.index('-ss')
      input = command.index('-i')
      expect(seek).to be < input
      expect(command.count('-ss')).to eq(1)
      expect(command[seek + 1]).to eq('4043.8')
      expect(command[command.index('-t') + 1]).to eq('3297.84')
      expect(command).to include('-c:s', 'copy')
    end
  end
end
