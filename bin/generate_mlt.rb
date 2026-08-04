#!/usr/bin/env ruby
# frozen_string_literal: true

require 'fileutils'
require_relative '../lib/video_encoder'

SOURCE = '/commun/to_be_cut/test_trimmer/The Truman Show.m2t'

output_path = ARGV.fetch(0, 'generated.mlt')

project = VideoEncoder::TrimProject.new(source: SOURCE)

project.add_segment(
  VideoEncoder::Segment.new(
    start_time: '01:02:40.000',
    end_time: '01:03:40.000'
  )
)

project.add_segment(
  VideoEncoder::Segment.new(
    start_time: '01:09:55.000',
    end_time: '01:10:55.000'
  )
)

builder = VideoEncoder::MltProjectBuilder.new
xml = builder.build(project)

FileUtils.mkdir_p(File.dirname(output_path))
File.write(output_path, xml)

puts "MLT project written to #{File.expand_path(output_path)}"
