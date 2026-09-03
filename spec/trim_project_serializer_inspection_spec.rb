# frozen_string_literal: true

RSpec.describe VideoEncoder::TrimProjectSerializer do
  describe '#dump' do
    it 'serializes the technical source inspection' do
      inspected_at = Time.new(
        2026,
        9,
        3,
        18,
        42,
        0,
        '+02:00'
      )
      video = VideoEncoder::VideoTrack.new(
        index: 0,
        type: :video,
        codec: 'h264',
        frame_rate: Rational(25, 1),
        width: 1920,
        height: 1080
      )
      audio = VideoEncoder::Track.new(
        index: 1,
        type: :audio,
        codec: 'eac3',
        language: 'fra',
        default: true
      )
      subtitle = VideoEncoder::Track.new(
        index: 4,
        type: :subtitle,
        codec: 'dvb_subtitle',
        language: 'fra',
        hearing_impaired: true
      )
      media = VideoEncoder::Media.new(
        path: '/commun/source-a.m2t',
        duration: 3_600,
        inspected_at: inspected_at,
        size_bytes: 6_581_393_080,
        video_tracks: [video],
        audio_tracks: [audio],
        subtitle_tracks: [subtitle]
      )

      project = VideoEncoder::TrimProject.new
      project.add_segment(
        VideoEncoder::Segment.new(
          source: media,
          start_frame: 0,
          end_frame: 1_499
        )
      )

      document = JSON.parse(
        described_class.new.dump(project)
      )

      inspection = document
                   .fetch('sources')
                   .first
                   .fetch('inspection')

      expect(inspection).to eq(
        'duration' => 3_600,
        'inspected_at' => '2026-09-03T18:42:00+02:00',
        'size_bytes' => 6_581_393_080,
        'video_tracks' => [
          {
            'index' => 0,
            'codec' => 'h264',
            'width' => 1920,
            'height' => 1080,
            'frame_rate' => {
              'numerator' => 25,
              'denominator' => 1
            }
          }
        ],
        'audio_tracks' => [
          {
            'index' => 1,
            'codec' => 'eac3',
            'language' => 'fra',
            'default' => true,
            'visual_impaired' => false
          }
        ],
        'subtitle_tracks' => [
          {
            'index' => 4,
            'codec' => 'dvb_subtitle',
            'language' => 'fra',
            'default' => false,
            'forced' => false,
            'hearing_impaired' => true
          }
        ]
      )
    end
  end
end
