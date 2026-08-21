# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::VideoExportProfile do
  describe '.hd_720p25' do
    it 'defines the video output policy' do
      profile = described_class.hd_720p25

      expect(profile.width).to eq(1280)
      expect(profile.height).to eq(720)
      expect(profile.frame_rate).to eq(Rational(25, 1))
      expect(profile).to be_progressive
      expect(profile.colorspace).to eq(709)
      expect(profile.display_aspect_ratio).to eq(Rational(16, 9))
      expect(profile.sample_aspect_ratio).to eq(Rational(1, 1))
    end
  end
end
