# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::FfmpegSubtitleProjectConcatenator do
  subject(:concatenator) do
    described_class.new(
      runner: runner,
      writer: writer
    )
  end

  let(:runner) { instance_double('CommandRunner') }
  let(:writer) { instance_double('ManifestWriter') }

  describe '#call' do
    it 'concatenates subtitle transports on an exact project timeline' do
      allow(writer).to receive(:write)
      allow(runner).to receive(:run)

      concatenator.call(
        segments: [
          {
            path: '/tmp/subtitle_segment_0.ts',
            duration: Rational(60, 1)
          },
          {
            path: '/tmp/subtitle_segment_1.ts',
            duration: Rational(60, 1)
          }
        ],
        manifest_path: '/tmp/subtitle_project.ffconcat',
        output_path: '/tmp/subtitle_project.ts'
      )

      expect(writer).to have_received(:write).with(
        '/tmp/subtitle_project.ffconcat',
        <<~FFCONCAT
          ffconcat version 1.0
          file '/tmp/subtitle_segment_0.ts'
          inpoint 0
          outpoint 60
          duration 60
          file '/tmp/subtitle_segment_1.ts'
          inpoint 0
          outpoint 60
          duration 60
        FFCONCAT
      )

      expect(runner).to have_received(:run).with(
        'ffmpeg',
        '-y',
        '-loglevel', 'warning',
        '-f', 'concat',
        '-safe', '0',
        '-i', '/tmp/subtitle_project.ffconcat',
        '-map', '0:v:0',
        '-map', '0:s:0',
        '-c', 'copy',
        '-muxdelay', '0',
        '-muxpreload', '0',
        '-f', 'mpegts',
        '/tmp/subtitle_project.ts'
      )
    end

    it 'escapes apostrophes in transport paths' do
      allow(writer).to receive(:write)
      allow(runner).to receive(:run)

      concatenator.call(
        segments: [
          {
            path:
              "/tmp/Alsace, terre d'orgues.ts",
            duration: Rational(60, 1)
          }
        ],
        manifest_path:
          '/tmp/subtitle_project.ffconcat',
        output_path:
          '/tmp/subtitle_project.ts'
      )

      expect(writer).to have_received(:write).with(
        '/tmp/subtitle_project.ffconcat',
        a_string_including(
          %q(file '/tmp/Alsace, terre d'\''orgues.ts')
        )
      )
    end
  end
end
