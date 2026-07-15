# frozen_string_literal: true

module VideoEncoder
  class EncodingMonitorFactory
    def self.build(source)
      duration = MediaInfo.new.duration(source)

      EncodingMonitor.new(
        parser: ProgressParser.new,
        progress: EncodingProgress.new(duration),
        reporter: ProgressReporter.new
      )
    end
  end
end
