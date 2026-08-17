# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimEditor do
  let(:media) { instance_double(VideoEncoder::Media) }
  let(:project) { instance_double(VideoEncoder::TrimProject) }

  subject(:editor) do
    described_class.new(
      media: media,
      project: project
    )
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

  describe '#validate_selection' do
    before do
      allow(project).to receive(:add_segment)
    end

    it 'adds the selected segment to the trim project' do
      editor.seek_to(12_345)
      editor.mark_in

      editor.seek_to(15_678)
      editor.mark_out

      editor.validate_selection

      expect(project).to have_received(:add_segment).with(
        VideoEncoder::Segment.new(
          start_frame: 12_345,
          end_frame: 15_678
        )
      )
    end

    it 'clears the selection after validation' do
      allow(project).to receive(:add_segment)
      editor.seek_to(12_345)
      editor.mark_in

      editor.seek_to(15_678)
      editor.mark_out

      editor.validate_selection

      expect(editor.in_frame).to be_nil
      expect(editor.out_frame).to be_nil
    end

    it 'rejects validation when no selection is defined' do
      expect do
        editor.validate_selection
      end.to raise_error(ArgumentError)
    end
  end
end
