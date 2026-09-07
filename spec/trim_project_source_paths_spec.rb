# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimProjectSourcePaths do
  subject(:reader) { described_class.new }

  it 'reads source paths from a version 1 project' do
    json = JSON.generate(
      format: 'video_encoder.trim_project',
      version: 1,
      timeline: [
        {
          type: 'segment',
          source: '/commun/to_be_cut/movie.m2t',
          start_frame: 100,
          end_frame: 200
        },
        {
          type: 'segment',
          source: '/commun/to_be_cut/movie.m2t',
          start_frame: 300,
          end_frame: 400
        }
      ]
    )

    expect(reader.call(json)).to eq(
      [
        Pathname(
          '/commun/to_be_cut/movie.m2t'
        )
      ]
    )
  end

  it 'reads source paths from a version 2 project' do
    json = JSON.generate(
      format: 'video_encoder.trim_project',
      version: 2,
      sources: [
        {
          id: 'source',
          path: '/commun/to_be_cut/movie.m2t'
        },
        {
          id: 'source_2',
          path: '/commun/to_be_cut/credits.m2t'
        }
      ],
      timeline: []
    )

    expect(reader.call(json)).to eq(
      [
        Pathname(
          '/commun/to_be_cut/movie.m2t'
        ),
        Pathname(
          '/commun/to_be_cut/credits.m2t'
        )
      ]
    )
  end
end
