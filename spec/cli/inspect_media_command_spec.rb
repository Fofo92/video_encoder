# frozen_string_literal: true

require 'spec_helper'
require 'json'
require 'stringio'

RSpec.describe VideoEncoder::CLI::InspectMediaCommand do
  it 'writes the source inspection as JSON' do
    media = instance_double(
      VideoEncoder::Media,
      path: Pathname('/commun/movie.m2t')
    )
    media_probe = instance_double(
      VideoEncoder::MediaProbe
    )
    serializer = instance_double(
      VideoEncoder::MediaInspectionSerializer
    )
    dependency_checker = instance_double(
      VideoEncoder::ExternalDependencyChecker
    )
    output = StringIO.new

    allow(dependency_checker).to receive(:call)
      .with('ffprobe')
    allow(media_probe).to receive(:read)
      .with('/commun/movie.m2t')
      .and_return(media)
    allow(serializer).to receive(:call)
      .with(media)
      .and_return(duration: 3_600)

    command = described_class.new(
      argv: ['/commun/movie.m2t'],
      dependency_checker: dependency_checker,
      media_probe: media_probe,
      serializer: serializer,
      output: output
    )

    command.run

    expect(dependency_checker).to have_received(:call)
      .with('ffprobe').once
    expect(media_probe).to have_received(:read)
      .with('/commun/movie.m2t').once
    expect(serializer).to have_received(:call)
      .with(media).once
    expect(JSON.parse(output.string)).to eq(
      'format' => 'video_encoder.media_inspection',
      'version' => 1,
      'source' => {
        'path' => '/commun/movie.m2t',
        'inspection' => {
          'duration' => 3_600
        }
      }
    )
  end
end
