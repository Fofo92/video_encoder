# frozen_string_literal: true

require 'spec_helper'
require 'json'
require 'rbconfig'
require 'rexml'
require 'tmpdir'

RSpec.describe 'Special-character paths across export boundaries' do
  JSON.parse(File.read(File.join(__dir__, 'fixtures/path_names.json'))).each do |name|
    context name do
      let(:source_path) { File.join('/tmp', name, "#{name}.m2t") }
      let(:media) { VideoEncoder::Media.new(path: source_path, duration: 1) }
      let(:project) do
        VideoEncoder::TrimProject.new.tap do |value|
          value.add_segment(VideoEncoder::Segment.new(source: media, start_frame: 0, end_frame: 24))
        end
      end

      it 'round-trips the source through project JSON and MLT XML' do
        json = VideoEncoder::TrimProjectSerializer.new.dump(project)
        probe = instance_double(VideoEncoder::MediaProbe)
        allow(probe).to receive(:read).with(source_path).and_return(media)
        restored = VideoEncoder::TrimProjectLoader.new(media_probe: probe).load(json)
        expect(restored.segments.first.source.path.to_s).to eq(source_path)
        expect(VideoEncoder::TrimProjectSourcePaths.new.call(json).map(&:to_s)).to eq([source_path])

        tracks = { media => double(frame_rate: Rational(25, 1), index: 0) }
        xml = VideoEncoder::MltProjectBuilder.new.build(restored, video_tracks_by_source: tracks)
        resources = REXML::Document.new(xml).get_elements('mlt/chain/property[@name="resource"]')
        expect(resources.map(&:text)).to eq([source_path])
      end

      it 'passes source, project, subtitle and output paths through a real process unchanged' do
        Dir.mktmpdir do |directory|
          capture = File.join(directory, 'arguments.json')
          paths = %w[m2t json ts srt mkv].map { |extension| File.join(directory, name, "#{name}.#{extension}") }
          VideoEncoder::CommandRunner.new.run(
            RbConfig.ruby, '-rjson', '-e', 'File.write(ARGV.shift, JSON.generate(ARGV))', capture, *paths
          )
          expect(JSON.parse(File.read(capture))).to eq(paths)
          expect(Dir.children(directory)).to eq(['arguments.json'])
        end
      end

      it 'opens the generated concat manifest with real FFmpeg' do
        Dir.mktmpdir do |directory|
          root = File.join(directory, name)
          Dir.mkdir(root)
          source = File.join(root, "#{name}.ts")
          manifest = File.join(root, "#{name}.ffconcat")
          runner = VideoEncoder::CommandRunner.new
          runner.run('ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                     'color=size=64x64:rate=25:duration=1', '-an', '-c:v', 'mpeg2video',
                     '-bf', '0', '-threads', '1', '-muxdelay', '0', '-muxpreload', '0', '-f', 'mpegts', source)
          concatenator = VideoEncoder::FfmpegSubtitleProjectConcatenator.new(
            runner: double.as_null_object, writer: File
          )
          concatenator.call(segments: [{ path: source, duration: Rational(1, 1) }],
                            manifest_path: manifest, output_path: File.join(root, 'joined.ts'))
          expect do
            runner.run('ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0',
                       '-i', manifest, '-map', '0:v:0', '-f', 'null', '-')
          end.not_to raise_error
        end
      end
    end
  end
end
