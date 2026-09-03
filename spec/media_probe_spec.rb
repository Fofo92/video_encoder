# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::MediaProbe do
  subject(:media_probe) { described_class.new }

  describe '#duration' do
    it 'returns the duration in seconds' do
      status = instance_double(Process::Status, success?: true)

      stdout = JSON.generate(
        'format' => {
          'duration' => '123.456'
        },
        'streams' => []
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return([stdout, '', status])

      expect(
        media_probe.duration('movie.m2t')
      ).to eq(123.456)
    end

    it 'raises when ffprobe fails' do
      status = instance_double(
        Process::Status,
        success?: false,
        exitstatus: 1
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return(['', "file not found\n", status])

      expect {
        media_probe.duration('movie.m2t')
      }.to raise_error(RuntimeError, /file not found/)
    end
  end

  describe '#read' do
    it 'preserves the probed file path' do
      status = instance_double(Process::Status, success?: true)

      stdout = JSON.generate(
        'format' => {
          'duration' => '123.456'
        },
        'streams' => []
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return([stdout, '', status])

      media = media_probe.read('movie.m2t')

      expect(media.path).to eq(Pathname('movie.m2t'))
    end

    it 'preserves the technical properties of a video track' do
      status = instance_double(
        Process::Status,
        success?: true
      )

      stdout = JSON.generate(
        'format' => {
          'duration' => '123.456'
        },
        'streams' => [
          {
            'index' => 0,
            'codec_type' => 'video',
            'codec_name' => 'h264',
            'width' => 1920,
            'height' => 1080,
            'avg_frame_rate' => '25/1',
            'tags' => {},
            'disposition' => {}
          }
        ]
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return([stdout, '', status])

      video_track = media_probe
                    .read('movie.m2t')
                    .video_tracks
                    .first

      expect(video_track.frame_rate)
        .to eq(Rational(25, 1))
      expect(video_track.width).to eq(1920)
      expect(video_track.height).to eq(1080)
    end

    it 'records when and at what size the source was inspected' do
      inspected_at = Time.new(
        2026,
        9,
        3,
        18,
        42,
        0,
        '+02:00'
      )
      clock = class_double(
        Time,
        now: inspected_at
      )
      status = instance_double(
        Process::Status,
        success?: true
      )

      stdout = JSON.generate(
        'format' => {
          'duration' => '123.456',
          'size' => '6581393080'
        },
        'streams' => []
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return([stdout, '', status])

      media = described_class
              .new(clock: clock)
              .read('movie.m2t')

      expect(media.inspected_at).to eq(inspected_at)
      expect(media.size_bytes).to eq(6_581_393_080)
    end
  end
end
