# frozen_string_literal: true

require 'spec_helper'
require 'tmpdir'
require 'rexml'

RSpec.describe VideoEncoder::TrimExporter, 'parallel audio' do
  around do |example|
    Dir.mktmpdir('parallel_export') do |directory|
      @directory = directory
      example.run
    end
  end

  let(:workspace) { VideoEncoder::TrimWorkspace.new(directory: @directory) }
  let(:batch) { instance_double(VideoEncoder::ParallelCommandRunner) }
  let(:renderer) { VideoEncoder::MltRenderer.new(runner: double('Runner'), parallel_runner: batch) }
  let(:remuxer) { instance_double(VideoEncoder::FfmpegRemuxer) }
  let(:timings) { VideoEncoder::ExportTimings.new }
  let(:events) { [] }
  let(:media) { VideoEncoder::Media.new(path: '/capture.m2t', duration: 60) }
  let(:video) { VideoEncoder::VideoTrack.new(index: 0, type: :video, frame_rate: Rational(50, 1)) }
  let(:project) do
    VideoEncoder::TrimProject.new.tap do |project|
      project.add_segment(VideoEncoder::Segment.new(source: media, start_frame: 101, end_frame: 198))
    end
  end
  let(:outputs) do
    %i[french original].each_with_index.map do |role, index|
      VideoEncoder::AudioOutputTrack.new(
        role: role,
        tracks_by_source: { media => VideoEncoder::Track.new(index: index + 1, type: :audio) }
      )
    end
  end

  def export(concurrency: 2, **options)
    described_class.new(
      builder: VideoEncoder::MltProjectBuilder.new,
      renderer: renderer, remuxer: remuxer, workspace: workspace,
      audio_concurrency: concurrency, timings: timings,
      progress_reporter: ->(**event) { events << event }, **options
    ).call(
      trim_project: project, video_tracks_by_source: { media => video },
      audio_output_tracks: outputs, output_path: File.join(@directory, 'movie.mkv')
    )
  end

  before do
    allow(renderer).to receive(:render_video)
    allow(remuxer).to receive(:remux)
  end

  it 'prepares isolated audio-only projects before either process starts' do
    allow(batch).to receive(:run) do |commands, limit:|
      expect(limit).to eq(2)
      expect(commands.length).to eq(2)
      commands.each_with_index do |command, index|
        document = REXML::Document.new(File.read(command[:argv][2]))
        expect(document.elements['mlt/chain/property[@name="video_index"]'].text).to eq('-1')
        expect(document.elements['mlt/chain/property[@name="audio_index"]'].text).to eq((index + 1).to_s)
        expect(document.elements['mlt/playlist/entry'].attributes['in']).to eq('50')
        expect(document.elements['mlt/playlist/entry'].attributes['out']).to eq('99')
      end
      # Completion order must not change the audio stream order in the final file.
      commands.reverse_each do |command|
        File.write(command[:argv][4].delete_prefix('avformat:'), 'audio')
      end
    end

    export

    expect(events.select { |event| event[:stage] == :audio }).to eq(
      [{ stage: :audio, step: 2, total: 4, tracks: 2, parallel: true }]
    )
    expect(remuxer).to have_received(:remux).with(
      video_path: workspace.video_path, output_path: File.join(@directory, 'movie.mkv'),
      audio_inputs: outputs.map { |track| { path: workspace.audio_path(track), output_track: track } }
    )
    expect(timings.entries.map { |entry| entry[:stage] }).to eq(%i[video subtitles audio remux])
    expect(timings.entries.find { |entry| entry[:stage] == :audio })
      .to include(concurrency: 2, roles: %i[french original], status: 'done')
  end

  it 'never remuxes after an audio process fails' do
    allow(batch).to receive(:run).and_raise('audio failed')

    expect { export }.to raise_error('audio failed')
    expect(remuxer).not_to have_received(:remux)
    expect(timings.entries.last).to include(stage: :audio, status: 'failed')
  end

  it 'can run the identical audio projects sequentially for a measured comparison' do
    allow(renderer).to receive(:render_audio)

    export(concurrency: 1)

    expect(renderer).to have_received(:render_audio).with(
      project_path: File.join(@directory, 'audio_french.mlt'), output_path: workspace.audio_path(outputs[0])
    ).ordered
    expect(renderer).to have_received(:render_audio).with(
      project_path: File.join(@directory, 'audio_original.mlt'), output_path: workspace.audio_path(outputs[1])
    ).ordered
    expect(timings.entries.find { |entry| entry[:stage] == :audio }).to include(concurrency: 1)
  end

  it 'does not reintroduce original audio omitted by the subtitle policy' do
    subtitles = instance_double(VideoEncoder::TrimSubtitleExporter, call: nil)
    allow(renderer).to receive(:render_audio)

    export(subtitle_exporter: subtitles)

    expect(renderer).to have_received(:render_audio).once.with(
      project_path: File.join(@directory, 'audio_french.mlt'), output_path: workspace.audio_path(outputs[0])
    )
    expect(File.exist?(File.join(@directory, 'audio_original.mlt'))).to be(false)
  end
end
