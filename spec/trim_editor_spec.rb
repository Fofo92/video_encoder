# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimEditor do
  let(:media) { instance_double(VideoEncoder::Media) }

  subject(:editor) do
    described_class.new(media: media)
  end

  describe '#media' do
    it 'returns the edited media' do
      expect(editor.media).to eq(media)
    end
  end

  describe '#current_frame' do
    it 'starts at the first frame' do
      expect(editor.current_frame).to eq(0)
    end
  end

  describe '#mark_in' do
    it 'stores the current frame as the in point' do
      editor.mark_in

      expect(editor.in_frame).to eq(0)
    end
  end

  describe '#seek_to' do
    it 'moves to the requested frame' do
      editor.seek_to(12_345)

      expect(editor.current_frame).to eq(12_345)
    end
  end

  describe '#mark_in' do
    it 'stores the current frame' do
      editor.seek_to(12_345)

      editor.mark_in

      expect(editor.in_frame).to eq(12_345)
    end
  end

  describe '#mark_out' do
    it 'stores the current frame as the out point' do
      editor.seek_to(15_678)

      editor.mark_out

      expect(editor.out_frame).to eq(15_678)
    end
  end

  it 'remembers both boundaries of a selection' do
    editor.seek_to(12_345)
    editor.mark_in

    editor.seek_to(15_678)
    editor.mark_out

    expect(editor.in_frame).to eq(12_345)
    expect(editor.out_frame).to eq(15_678)
  end
end
