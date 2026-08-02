RSpec.describe VideoEncoder::TrimProject do
  let(:media) { instance_double(VideoEncoder::Media) }

  subject(:project) { described_class.new(source: media) }

  describe '#segments' do
    it 'is initially empty' do
      expect(project.segments).to be_empty
    end
  end

  describe '#add_segment' do
    it 'adds a segment to the project' do
      segment = VideoEncoder::Segment.new(
        start_time: '01:02:40.000',
        end_time: '01:03:40.000'
      )

      project.add_segment(segment)

      expect(project.segments).to eq([segment])
    end

    it 'preserves the insertion order' do
      first = VideoEncoder::Segment.new(
        start_time: '00:10:00.000',
        end_time: '00:11:00.000'
      )

      second = VideoEncoder::Segment.new(
        start_time: '00:20:00.000',
        end_time: '00:21:00.000'
      )

      project.add_segment(first)
      project.add_segment(second)

      expect(project.segments).to eq([first, second])
    end

    it 'rejects overlapping segments' do
      first = VideoEncoder::Segment.new(
        start_time: '01:00:00.000',
        end_time:   '01:10:00.000'
      )

      second = VideoEncoder::Segment.new(
        start_time: '01:05:00.000',
        end_time:   '01:15:00.000'
      )

      project.add_segment(first)

      expect do
        project.add_segment(second)
      end.to raise_error(ArgumentError)
    end

    it 'rejects contiguous segments' do
      first = VideoEncoder::Segment.new(
        start_time: '01:00:00.000',
        end_time:   '01:10:00.000'
      )

      second = VideoEncoder::Segment.new(
        start_time: '01:10:00.000',
        end_time:   '01:20:00.000'
      )

      project.add_segment(first)

      expect do
        project.add_segment(second)
      end.to raise_error(ArgumentError)
    end
  end

  describe '#source' do
    it 'returns the source media' do
      media = instance_double(VideoEncoder::Media)

      project = described_class.new(source: media)

      expect(project.source).to eq(media)
    end
  end

  describe '#duration' do
    it 'returns the total duration of all segments in milliseconds' do
      first = VideoEncoder::Segment.new(
        start_time: '00:10:00.000',
        end_time:   '00:11:00.250'
      )

      second = VideoEncoder::Segment.new(
        start_time: '00:20:00.000',
        end_time:   '00:21:30.500'
      )

      project.add_segment(first)
      project.add_segment(second)

      expect(project.duration).to eq(150_750)
    end
  end
end
