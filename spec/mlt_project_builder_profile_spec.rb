# frozen_string_literal: true

require 'spec_helper'
require 'rexml'

RSpec.describe VideoEncoder::MltProjectBuilder do
  describe '#build with an export profile' do
    it 'builds the MLT profile from the configured export profile' do
      media = instance_double(
        VideoEncoder::Media,
        path: Pathname('/media/source.mkv')
      )

      project = VideoEncoder::TrimProject.new
      project.add_segment(
        VideoEncoder::Segment.new(
          source: media,
          start_time: '00:00:00.000',
          end_time: '00:00:10.000'
        )
      )

      profile = VideoEncoder::VideoExportProfile.new(
        width: 640,
        height: 360,
        frame_rate: Rational(24, 1),
        progressive: true,
        colorspace: 601,
        display_aspect_ratio: Rational(16, 9),
        sample_aspect_ratio: Rational(1, 1)
      )

      xml = described_class.new(profile: profile).build(project)
      document = REXML::Document.new(xml)
      mlt_profile = REXML::XPath.first(document, '/mlt/profile')
      attributes = {}

      mlt_profile.attributes.each_attribute do |attribute|
        attributes[attribute.name] = attribute.value
      end

      expect(attributes).to include(
        'colorspace' => '601',
        'display_aspect_den' => '9',
        'display_aspect_num' => '16',
        'frame_rate_den' => '1',
        'frame_rate_num' => '24',
        'height' => '360',
        'progressive' => '1',
        'sample_aspect_den' => '1',
        'sample_aspect_num' => '1',
        'width' => '640'
      )
    end
  end
end
