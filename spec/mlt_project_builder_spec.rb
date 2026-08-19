# frozen_string_literal: true

require 'spec_helper'
require 'rexml'
require 'open3'
require 'tempfile'

RSpec.describe VideoEncoder::MltProjectBuilder do
  subject(:builder) { described_class.new }

  let(:source) { '/commun/The Truman Show.m2t' }
  let(:media) { instance_double(VideoEncoder::Media) }

  let(:project) do
    VideoEncoder::TrimProject.new(source: source).tap do |trim_project|
      trim_project.add_segment(
        VideoEncoder::Segment.new(
          source: media,
          start_time: '01:02:40.000',
          end_time: '01:03:40.000'
        )
      )

      trim_project.add_segment(
        VideoEncoder::Segment.new(
          source: media,
          start_time: '01:09:55.000',
          end_time: '01:10:55.000'
        )
      )
    end
  end

  describe '#build' do
    it 'returns an XML document' do
      xml = builder.build(project)

      expect(xml).to include('<mlt')
      expect(xml).to include('</mlt>')
    end

    it 'declares the media source' do
      xml = builder.build(project)

      expect(xml).to include(
        '<property name="resource">/commun/The Truman Show.m2t</property>'
      )
    end

    it 'creates one playlist entry per segment' do
      xml = builder.build(project)

      expect(xml.scan('<entry ')).to have_attributes(size: 2)
    end

    it 'preserves the order of the segments' do
      xml = builder.build(project)

      first_position = xml.index('in="01:02:40.000"')
      second_position = xml.index('in="01:09:55.000"')

      expect(first_position).to be < second_position
    end

    it 'builds a playlist containing the project segments' do
      xml = builder.build(project)

      expect(xml).to include(
        '<entry in="01:02:40.000" out="01:03:40.000" producer="source"/>'
      )

      expect(xml).to include(
        '<entry in="01:09:55.000" out="01:10:55.000" producer="source"/>'
      )
    end

    it 'declares the 1080i 25 fps profile' do
      document = REXML::Document.new(builder.build(project))
      profile = document.elements['mlt/profile']

      expect(profile.attributes['description']).to eq('HD 1080i 25 fps')

      expect(profile.attributes['width']).to eq('1920')
      expect(profile.attributes['height']).to eq('1080')

      expect(profile.attributes['frame_rate_den']).to eq('1')
      expect(profile.attributes['frame_rate_num']).to eq('25')

      expect(profile.attributes['progressive']).to eq('0')
      expect(profile.attributes['colorspace']).to eq('709')

      expect(profile.attributes['display_aspect_den']).to eq('9')
      expect(profile.attributes['display_aspect_num']).to eq('16')

      expect(profile.attributes['sample_aspect_den']).to eq('1')
      expect(profile.attributes['sample_aspect_num']).to eq('1')
    end

    it 'produces a document accepted by melt', :integration do
      xml = builder.build(project)

      Tempfile.create(['video_encoder', '.mlt']) do |file|
        file.write(xml)
        file.flush

        _stdout, stderr, status = Open3.capture3(
          'melt-7',
          file.path,
          '-consumer',
          'null',
          'terminate_on_pause=1',
          'real_time=-1'
        )

        expect(status).to be_success, stderr
      end
    end

    it 'selects the requested audio and video streams' do
      xml = builder.build(
        project,
        video_index: 0,
        audio_index: 1
      )

      document = REXML::Document.new(xml)
      chain = document.elements['mlt/chain[@id="source"]']

      expect(chain.elements['property[@name="video_index"]'].text).to eq('0')
      expect(chain.elements['property[@name="audio_index"]'].text).to eq('1')
    end

    it 'can disable the audio stream' do
      xml = builder.build(
        project,
        video_index: 0,
        audio_index: -1
      )

      document = REXML::Document.new(xml)
      chain = document.elements['mlt/chain[@id="source"]']

      expect(chain.elements['property[@name="audio_index"]'].text).to eq('-1')
    end
  end
end
