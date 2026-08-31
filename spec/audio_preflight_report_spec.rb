# frozen_string_literal: true

require 'spec_helper'
require 'json'
require 'pathname'

RSpec.describe VideoEncoder::AudioPreflightReport do
  it 'serializes a silent audio result into JSON-compatible data' do
    source = instance_double(
      VideoEncoder::Media,
      path: Pathname.new('/recordings/movie.ts')
    )
    track = VideoEncoder::Track.new(
      index: 1,
      type: :audio,
      language: 'fra'
    )

    results = [
      {
        source: source,
        track: track,
        start_frame: 750,
        end_frame: 2249,
        frame_rate: Rational(25, 1),
        analysis: {
          status: :inconclusive,
          sample_count: 2_880_000,
          mean_volume_db: -Float::INFINITY,
          max_volume_db: -Float::INFINITY
        }
      }
    ]

    json = described_class.new.call(results)

    expect(JSON.parse(json)).to eq(
      {
        'version' => 1,
        'audio_checks' => [
          {
            'source' => '/recordings/movie.ts',
            'track_index' => 1,
            'language' => 'fra',
            'start_frame' => 750,
            'end_frame' => 2249,
            'frame_rate' => {
              'numerator' => 25,
              'denominator' => 1
            },
            'analysis' => {
              'status' => 'inconclusive',
              'sample_count' => 2_880_000,
              'mean_volume_db' => '-inf',
              'max_volume_db' => '-inf'
            }
          }
        ]
      }
    )
  end
end
