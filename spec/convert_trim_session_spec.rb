# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::ConvertTrimSession do
  subject(:converter) do
    described_class.new(
      loader: loader,
      serializer: serializer
    )
  end

  let(:loader) do
    instance_double(VideoEncoder::TrimSessionLoader)
  end

  let(:serializer) do
    instance_double(VideoEncoder::TrimProjectSerializer)
  end

  let(:project) do
    instance_double(VideoEncoder::TrimProject)
  end

  it 'serializes the project built from the editing session' do
    allow(loader).to receive(:load)
      .with('editing session')
      .and_return(project)

    allow(serializer).to receive(:dump)
      .with(project)
      .and_return('persistent project')

    expect(converter.call('editing session'))
      .to eq('persistent project')
  end
end
