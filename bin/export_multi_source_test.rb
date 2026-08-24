#!/usr/bin/env ruby
# frozen_string_literal: true

require 'fileutils'
require_relative '../lib/video_encoder'

source_a_path = ARGV.fetch(0)
source_c_path = ARGV.fetch(1)

output_path = File.expand_path(
  ARGV.fetch(2, '/tmp/video_encoder_multi_source_full.mkv')
)

probe = VideoEncoder::MediaProbe.new
media_a = probe.read(source_a_path)
media_c = probe.read(source_c_path)

video_a = media_a.video_tracks.first
video_c = media_c.video_tracks.first

segment_for = lambda do |media, video_track, start_seconds, duration|
  frame_rate = video_track.frame_rate
  start_frame = (start_seconds * frame_rate).round
  exclusive_end_frame = ((start_seconds + duration) * frame_rate).round

  VideoEncoder::Segment.new(
    source: media,
    start_frame: start_frame,
    end_frame: exclusive_end_frame - 1
  )
end

project = VideoEncoder::TrimProject.new

project.add_segment(segment_for.call(media_a, video_a, 1200, 60))
project.add_segment(segment_for.call(media_c, video_c, 1200, 60))
project.add_segment(segment_for.call(media_a, video_a, 1320, 60))

workspace_directory = File.join(
  File.dirname(output_path),
  'video_encoder_multi_source_workspace'
)

FileUtils.mkdir_p(workspace_directory)

ENV['VIDEO_ENCODER_WORKSPACE'] = workspace_directory

runner = VideoEncoder::CommandRunner.new

service = VideoEncoder::TrimExportFactory.new(
  runner: runner,
  ccextractor_executable:
    ENV.fetch('CCEXTRACTOR_EXECUTABLE', 'ccextractor'),
  synchronization_delay: 0
).build(
  workspace_directory: workspace_directory
)

service.call(
  trim_project: project,
  output_path: output_path
)

puts "Export written to #{output_path}"
puts "A frame rate: #{video_a.frame_rate}"
puts "C frame rate: #{video_c.frame_rate}"
