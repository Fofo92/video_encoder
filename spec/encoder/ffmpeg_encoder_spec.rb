# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::Encoder::FFmpegEncoder do
  let(:logger) { instance_double(Logger, info: nil, error: nil) }
  let(:runner) { instance_double(VideoEncoder::Encoder::FFmpegRunner, run: nil) }
  let(:monitor) do
    instance_double(
      VideoEncoder::EncodingMonitor,
      call: nil,
      finish: nil
    )
  end

  let(:monitor_factory) do
    class_double(
      VideoEncoder::EncodingMonitorFactory,
      build: monitor
    )
  end

  let(:config) do
    instance_double(
      VideoEncoder::FFmpegConfig,
    container: 'mkv',
    video_codec: 'hevc_nvenc',
    preset: 'p6',
    tune: 'hq',
    rc: 'vbr_hq',
    cq: 22,
    deinterlace: true,
    spatial_aq: true,
    aq_strength: 8,
    b_ref_mode: 'middle',
    audio_codec: 'aac'
    )
  end

  subject(:encoder) do
    described_class.new(logger: logger, config: config, runner: runner, monitor_factory: monitor_factory)
  end

  let(:job) do
    VideoEncoder::Job.new(source: 'video.mkv')
  end

  describe '#encode' do
    it 'invokes the runner with the ffmpeg command' do
      encoder.encode(job)

      expect(runner).to have_received(:run).with(
      [
        'ffmpeg',
        '-y',
        '-progress', 'pipe:1',
        '-nostats',
        '-i', 'video.mkv',
        '-vf', 'bwdif,scale=w=1280:h=720:force_original_aspect_ratio=decrease',
        '-c:v', 'hevc_nvenc',
        '-preset', 'p6',
        '-tune', 'hq',
        '-rc', 'vbr_hq',
        '-cq', '22',
        '-spatial_aq', '1',
        '-aq-strength', '8',
        '-b_ref_mode', 'middle',
        '-c:a', 'aac',
        'video.mkv'
      ]
    )
    end
  end


  context 'when ffmpeg fails' do
    before do
      allow(runner)
        .to receive(:run)
        .and_raise(RuntimeError, 'input file not found')
    end

    it 'raises an exception with ffmpeg stderr' do
      expect { encoder.encode(job) }
        .to raise_error(RuntimeError, /input file not found/)
    end
  end
end
