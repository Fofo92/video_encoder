# frozen_string_literal: true

require 'spec_helper'
require 'rexml'

RSpec.describe VideoEncoder::MltProjectBuilder do
  describe 'XML resource escaping' do
    [
      '/commun/to_be_cut/Fast & Furious 4.m2t',
      '/commun/to_be_cut/Film <version> avec "guillemets".m2t',
      "/commun/to_be_cut/L'été & l'hiver.m2t",
      '/commun/to_be_cut/Literal &amp; in filename.m2t'
    ].each do |path|
      it "preserves the exact resource path after XML parsing: #{path}" do
        media = instance_double(VideoEncoder::Media, path: Pathname(path))
        project = VideoEncoder::TrimProject.new
        2.times do |index|
          project.add_segment(
            VideoEncoder::Segment.new(
              source: media,
              start_time: index.zero? ? '00:00:00.000' : '00:00:20.000',
              end_time: index.zero? ? '00:00:10.000' : '00:00:30.000'
            )
          )
        end

        xml = described_class.new.build(project)
        document = REXML::Document.new(xml)
        resources = document.get_elements('mlt/chain/property[@name="resource"]')

        expect(resources.map(&:text)).to eq([path, path])
        expect(document.get_elements('mlt/playlist/entry').size).to eq(2)
      end
    end
  end
end
