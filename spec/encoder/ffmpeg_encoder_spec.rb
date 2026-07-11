# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Encoder::FFmpegEncoder do
  let(:logger) { instance_double(Logger, info: nil, error: nil) }

  let(:config) do
    instance_double(
      VideoEncoder::FFmpegConfig,
      video_codec: 'hevc_nvenc',
      audio_codec: 'aac',
      preset: 'p6',
      crf: 22
    )
  end

  subject(:encoder) do
    described_class.new(logger: logger, config: config)
  end

  let(:job) do
    VideoEncoder::Job.new(source: 'video.mkv')
  end

  describe '#encode' do
    before do
      success = instance_double(Process::Status, success?: true)

      allow(Open3)
        .to receive(:capture3)
        .and_return(['', '', success])
    end

    it 'invokes ffmpeg' do
      encoder.encode(job)

        # expect(Open3).to have_received(:capture3)
        expect(Open3).to have_received(:capture3).with(
          'ffmpeg',
          '-y',
          '-i', 'video.mkv',
          '-c:v', 'hevc_nvenc',
          '-preset', 'p6',
          '-tune', 'hq',
          '-cq', '22',
          'rc', 'vbr',
          'spatial_aq', 'true',
          'b_ref_mode', 'middle',
          'deinterlace', 'true',
          '-c:a', 'aac',
          'video.mkv'
        )
      end
  end

  context 'when ffmpeg fails' do
    before do
      failure = instance_double(
        Process::Status,
        success?: false,
        exitstatus: 1
      )

      allow(Open3)
        .to receive(:capture3)
        .and_return(['', 'input file not found', failure])
    end

    it 'raises an exception with ffmpeg stderr' do
      expect { encoder.encode(job) }
        .to raise_error(RuntimeError, /input file not found/)
    end
  end
end
