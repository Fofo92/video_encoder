# frozen_string_literal: true

module VideoEncoder
  # Associates audio preflight samples with their analysis results.
  class AudioPreflightChecker
    def initialize(analyzer:)
      @analyzer = analyzer
    end

    def call(samples)
      samples.filter_map do |sample|
        next unless sample.fetch(:track).type == :audio

        sample.merge(analysis: analyzer.call(sample))
      end
    end

    private

    attr_reader :analyzer
  end
end
