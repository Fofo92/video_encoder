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
      rc: 'vbr',
      cq: 22,
      deinterlace: true,
      spatial_aq: true,
      aq_strength: 8,
      b_ref_mode: 'middle',
      audio_codec: 'aac'
    )
  end

  let(:selector) do
    instance_double(VideoEncoder::TrackSelector)
  end

  let(:media_probe) do
    instance_double(VideoEncoder::MediaProbe)
  end

  let(:video_track) do
  VideoEncoder::Track.new(
    index: 0,
    type: :video,
    codec: 'h264'
  )
end

let(:audio_track) do
  VideoEncoder::Track.new(
    index: 1,
    type: :audio,
    language: 'fra',
    codec:'aac'
  )
end

let(:original_audio_track) do
  VideoEncoder::Track.new(
    index: 4,
    type: :audio,
    language: 'deu',
    codec: 'eac3'
  )
end

let(:subtitle_track) do
  VideoEncoder::Track.new(
    index: 6,
    type: :subtitle,
    language: 'fra',
    codec: 'dvb_subtitle'
  )
end

let(:media) do
  VideoEncoder::Media.new(
    duration: 100,
    video_tracks: [video_track],
    audio_tracks: [audio_track, original_audio_track],
    subtitle_tracks: [subtitle_track]
  )
end

let(:selection) do
  {
    video: video_track,
    audio: [audio_track, original_audio_track],
    subtitles: [subtitle_track]
  }
end

  subject(:encoder) do
    described_class.new(
      logger: logger,
      config: config,
      runner: runner,
      monitor_factory: monitor_factory,
      selector: selector,
      media_probe: media_probe
    )
  end

  let(:job) do
    VideoEncoder::Job.new(source: 'video.mkv')
  end

  describe '#encode' do
    before do
      allow(media_probe)
        .to receive(:read)
        .with('video.mkv')
        .and_return(media)

      allow(selector)
        .to receive(:select)
        .with(media)
        .and_return(selection)

      allow(monitor_factory)
        .to receive(:build)
        .and_return(monitor)

      allow(monitor).to receive(:call)
      allow(monitor).to receive(:finish)
    end

    it 'invokes the runner with the ffmpeg command' do
      encoder.encode(job)

      expect(runner).to have_received(:run).with(
        [
          'ffmpeg',
          '-y',
          '-progress', 'pipe:1',
          '-nostats',
          '-i', 'video.mkv',
          '-map', '0:0',
          '-map', '0:1',
          '-map', '0:4',
          '-map', '0:6',
          '-vf', 'bwdif,scale=w=1280:h=720:force_original_aspect_ratio=decrease',
          '-c:v', 'hevc_nvenc',
          '-preset', 'p6',
          '-tune', 'hq',
          '-rc', 'vbr',
          '-cq', '30',
          '-b:v', '0',
          '-maxrate', '3M',
          '-bufsize', '6M',
          '-spatial_aq', '1',
          '-aq-strength', '8',
          '-b_ref_mode', 'middle',
          '-c:a', 'aac',
          '-b:a', '160k',
          '-ac', '2',
          '-disposition:v:0', 'default',
          '-disposition:a:0', 'default',
          'video.mkv'
        ]
      )
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
end
