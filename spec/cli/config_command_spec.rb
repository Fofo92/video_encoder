# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::CLI::ConfigCommand do
  describe '#run' do
    it 'prints the application configuration' do
      directories = double(
        'Directories',
        incoming: '/media/incoming',
        queue: '/media/queue',
        encoded: '/media/encoded',
        archive: '/media/archive'
      )

      ffmpeg = double(
        'FfmpegConfig',
        container: 'mkv',
        video_codec: 'hevc_nvenc',
        preset: 'p6',
        tune: 'hq',
        rc: 'vbr',
        cq: 30,
        audio_codec: 'aac'
      )

      config = instance_double(
        VideoEncoder::Config,
        database: '/data/video_encoder.db',
        encoder: 'ffmpeg',
        directories: directories,
        ffmpeg: ffmpeg
      )

      command = described_class.new(config: config)

      expect do
        command.run
      end.to output(
        a_string_including(
          'Database: /data/video_encoder.db',
          'Encoder:  ffmpeg',
          'Incoming: /media/incoming',
          'Queue:    /media/queue',
          'Encoded:  /media/encoded',
          'Archive:  /media/archive',
          'Container:   mkv',
          'Video codec: hevc_nvenc',
          'Preset:      p6',
          'Tune:        hq',
          'RC:          vbr',
          'CQ:          30',
          'Audio codec: aac'
        )
      ).to_stdout
    end
  end
end
