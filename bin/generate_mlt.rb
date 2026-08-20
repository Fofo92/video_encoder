#!/usr/bin/env ruby
# frozen_string_literal: true

require 'fileutils'
require_relative '../lib/video_encoder'

SOURCE = '/commun/to_be_cut/test_trimmer/The Truman Show.m2t'

output_path = ARGV.fetch(0, 'generated.mlt')
video_index = Integer(ARGV.fetch(1, 0))
audio_index = Integer(ARGV.fetch(2, 0))

project = VideoEncoder::TrimProject.new
media = VideoEncoder::MediaProbe.new.read(SOURCE)

project.add_segment(
  VideoEncoder::Segment.new(
    source: media,
    start_time: '01:02:40.000',
    end_time: '01:03:40.000'
  )
)

project.add_segment(
  VideoEncoder::Segment.new(
    source: media,
    start_time: '01:09:55.000',
    end_time: '01:10:55.000'
  )
)

builder = VideoEncoder::MltProjectBuilder.new
xml = builder.build(
  project,
  video_index: video_index,
  audio_index: audio_index
)

FileUtils.mkdir_p(File.dirname(output_path))
File.write(output_path, xml)

puts "MLT project written to #{File.expand_path(output_path)}"
