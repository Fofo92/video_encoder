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

    it 'preserves the frame rate of a video track' do
      status = instance_double(Process::Status, success?: true)

      stdout = JSON.generate(
        'format' => {
          'duration' => '123.456'
        },
        'streams' => [
          {
            'index' => 0,
            'codec_type' => 'video',
            'codec_name' => 'h264',
            'avg_frame_rate' => '25/1',
            'tags' => {},
            'disposition' => {}
          }
        ]
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return([stdout, '', status])

      media = media_probe.read('movie.m2t')

      expect(media.video_tracks.first.frame_rate).to eq(Rational(25, 1))
    end
  end
end
