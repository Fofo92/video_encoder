# frozen_string_literal: true

require 'spec_helper'

RSpec.describe VideoEncoder::TrimEditor do
  #  testing workflow A′ → C → B′ with 2 editors
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
          source: media,
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

  describe '#insert_gap' do
    it 'adds a gap expressed in frames to the project' do
      video_track = instance_double(
        VideoEncoder::VideoTrack,
        frame_rate: Rational(25, 1)
      )

      allow(media).to receive(:video_tracks)
        .and_return([video_track])

      allow(project).to receive(:add_gap)

      editor.insert_gap(duration: 2)

      expect(project).to have_received(:add_gap).with(
        VideoEncoder::Gap.new(frame_count: 50)
      )
    end

    it 'rounds the gap duration to the nearest frame' do
      video_track = instance_double(
        VideoEncoder::VideoTrack,
        frame_rate: Rational(25, 1)
      )

      allow(media).to receive(:video_tracks)
        .and_return([video_track])

      allow(project).to receive(:add_gap)

      editor.insert_gap(duration: 1.5)

      expect(project).to have_received(:add_gap).with(
        VideoEncoder::Gap.new(frame_count: 38)
      )
    end
  end

  describe 'building a timeline with a gap' do
    it 'places a gap between two validated segments' do
      video_track = instance_double(
        VideoEncoder::VideoTrack,
        frame_rate: Rational(25, 1)
      )

      allow(media).to receive(:video_tracks)
        .and_return([video_track])

      project = VideoEncoder::TrimProject.new(source: media)
      editor = described_class.new(
        media: media,
        project: project
      )

      editor.seek_to(1_000)
      editor.mark_in
      editor.seek_to(2_000)
      editor.mark_out
      editor.validate_selection

      editor.insert_gap(duration: 2)

      editor.seek_to(3_000)
      editor.mark_in
      editor.seek_to(4_000)
      editor.mark_out
      editor.validate_selection

      expect(project.timeline).to eq(
        [
          VideoEncoder::Segment.new(
            source: media,
            start_frame: 1_000,
            end_frame: 2_000
          ),
          VideoEncoder::Gap.new(frame_count: 50),
          VideoEncoder::Segment.new(
            source: media,
            start_frame: 3_000,
            end_frame: 4_000
          )
        ]
      )
    end
  end

  describe 'building a project from multiple media sources' do
    it 'builds A prime, C, B prime from two media sources' do
      media_a = instance_double(VideoEncoder::Media)
      media_c = instance_double(VideoEncoder::Media)

      project = VideoEncoder::TrimProject.new(source: media_a)

      editor_a = described_class.new(
        media: media_a,
        project: project
      )

      editor_c = described_class.new(
        media: media_c,
        project: project
      )

      # A′
      editor_a.seek_to(0)
      editor_a.mark_in
      editor_a.seek_to(1_999)
      editor_a.mark_out
      editor_a.validate_selection

      # C
      editor_c.seek_to(500)
      editor_c.mark_in
      editor_c.seek_to(999)
      editor_c.mark_out
      editor_c.validate_selection

      # B′
      editor_a.seek_to(3_000)
      editor_a.mark_in
      editor_a.seek_to(4_999)
      editor_a.mark_out
      editor_a.validate_selection

      expect(project.timeline).to eq(
        [
          VideoEncoder::Segment.new(
            source: media_a,
            start_frame: 0,
            end_frame: 1_999
          ),
          VideoEncoder::Segment.new(
            source: media_c,
            start_frame: 500,
            end_frame: 999
          ),
          VideoEncoder::Segment.new(
            source: media_a,
            start_frame: 3_000,
            end_frame: 4_999
          )
        ]
      )
    end
  end
end
