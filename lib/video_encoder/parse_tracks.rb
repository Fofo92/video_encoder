def parse_tracks(json, type)
  json.fetch('streams', [])
      .select { |stream| stream['codec_type'] == type }
      .map do |stream|
        Track.new(
          index: stream['index'],
          type: type.to_sym,
          codec: stream['codec_name'],
          language: stream.dig('tags', 'language'),
          default: stream.dig('disposition', 'default') == 1,
          forced: stream.dig('disposition', 'forced') == 1,
          hearing_impaired:
            stream.dig('disposition', 'hearing_impaired') == 1,
          visual_impaired:
            stream.dig('disposition', 'visual_impaired') == 1
        )
      end
end
