#!/usr/bin/env ruby
# frozen_string_literal: true

# Exploratory candidate refinement in the reset full-decoded-video clock.
# Proposals are diagnostics only: no project writes, export, source deletion.
require 'json'
require 'open3'
require 'optparse'
require 'pathname'
require_relative 'ad_separator_pairing'

def describe_frame(bytes)
  values = bytes.unpack('C*')
  patches = [[2, 3], [54, 3], [2, 27], [54, 27]].map do |x0, y0|
    patch = (y0...(y0 + 6)).flat_map { |y| values.slice(y * 64 + x0, 8) }
    mean = patch.sum.fdiv(patch.length)
    [mean, Math.sqrt(patch.sum { |v| (v - mean)**2 }.fdiv(patch.length))]
  end
  # Smooth outer-field model. Exclude the central animated logo/PUB lettering.
  agreeing = 0
  total = 0
  (3...33).each do |y|
    (2...62).each do |x|
      next if x.between?(14, 49) && y.between?(8, 28)
      fx = [[(x - 5.5) / 52.0, 0].max, 1].min
      fy = [[(y - 5.5) / 24.0, 0].max, 1].min
      top = patches[0][0] * (1 - fx) + patches[1][0] * fx
      bottom = patches[2][0] * (1 - fx) + patches[3][0] * fx
      expected = top * (1 - fy) + bottom * fy
      agreeing += 1 if (values[y * 64 + x] - expected).abs <= 40
      total += 1
    end
  end
  black_fraction = values.count { |v| v <= 32 }.fdiv(values.length)
  graphic_fraction = agreeing.fdiv(total)
  { black: black_fraction >= 0.98, graphic: black_fraction < 0.98 &&
      graphic_fraction >= 0.75 && patches.all? { |p| p[1] <= 25 },
    black_fraction: black_fraction, smooth_outer_fraction: graphic_fraction,
    corner_means: patches.map(&:first) }
end

def contiguous_runs(flags)
  runs = []
  flags.each_with_index do |flag, index|
    next unless flag
    if runs.last && runs.last[1] == index - 1
      runs.last[1] = index
    else
      runs << [index, index]
    end
  end
  runs
end

options = { repo: '/home/pascal/code/Fofo92/video_encoder' }
OptionParser.new do |p|
  p.banner = 'Usage: ruby refine_6ter_candidates.rb --candidates JSON --output NEW_DIRECTORY [--reference-corpus JSON]'
  p.on('--candidates PATH') { |v| options[:candidates] = v }
  p.on('--output PATH') { |v| options[:output] = v }
  p.on('--repo PATH') { |v| options[:repo] = v }
  p.on('--reuse-cache PATH') { |v| options[:reuse_cache] = v }
  p.on('--reference-corpus PATH') { |v| options[:reference] = v }
end.parse!

begin
  raise ArgumentError, '--candidates and --output required; no positional arguments' unless options[:candidates] && options[:output] && ARGV.empty?
  coarse = JSON.parse(File.read(options[:candidates]))
  unless coarse['format'] == 'video_encoder.6ter_pub_candidates' && coarse['complete'] && coarse['requested_start_seconds'].nil?
    raise ArgumentError, 'a completed full-source scan is required (no --start)'
  end
  source = coarse.fetch('source')
  raise ArgumentError, "source unavailable: #{source}" unless File.file?(source)
  probe_text, probe_error, probe_status = Open3.capture3('ffprobe', '-v', 'error', '-show_streams', '-of', 'json', source)
  raise "FFprobe failed: #{probe_error}" unless probe_status.success?
  probe = JSON.parse(probe_text)
  video = probe.fetch('streams').find { |s| s['codec_type'] == 'video' }
  raise ArgumentError, '25 fps average required for this pilot' unless Rational(video.fetch('avg_frame_rate')) == 25
  windows = coarse.fetch('candidates').each_with_index.map do |candidate, index|
    first = candidate.fetch('first_matching_sample_seconds')
    last = candidate.fetch('last_matching_sample_seconds')
    { id: index + 1, candidate: candidate, start: [(first * 25).floor - 300, 0].max,
      finish: (last * 25).ceil + 200, frames: [] }
  end
  raise ArgumentError, 'no candidates' if windows.empty?
  output = File.expand_path(options[:output])
  Dir.mkdir(output)
  command = ['ffmpeg', '-hide_banner', '-nostdin', '-nostats', '-loglevel', 'warning',
             '-threads', '2', '-i', source, '-map', "0:#{video.fetch('index')}", '-an', '-sn', '-dn',
             '-filter_threads', '1', '-vf', 'setpts=PTS-STARTPTS,scale=64:36,format=gray,fps=25',
             '-fps_mode', 'passthrough', '-threads', '1', '-f', 'rawvideo', 'pipe:1']
  count = 0
  started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  if options[:reuse_cache]
    cache = File.expand_path(options[:reuse_cache])
    manifest = JSON.parse(File.read(File.join(cache, 'window-cache.json')))
    signature = [source, File.size(source), File.mtime(source).to_f]
    raise 'Cached source differs from current source' unless manifest.fetch('source_signature') == signature
    count = manifest.fetch('decoded_frames')
    windows.each do |window|
      expected = { 'id' => window[:id], 'start' => window[:start], 'finish' => window[:finish] }
      raise 'Cached window definition differs' unless manifest.fetch('windows').include?(expected)
      bytes = File.binread(File.join(cache, format('window-%02d.gray', window[:id])))
      raise 'Invalid cached frame size' unless (bytes.bytesize % 2304).zero?
      window[:frames] = Array.new(bytes.bytesize / 2304) { |i| bytes.byteslice(i * 2304, 2304) }
    end
    warn 'Reusing candidate windows; no full-source decoding.'
  else
  warn 'One full-source pass at 25 fps; retaining only candidate neighbourhoods.'
  File.open(File.join(output, 'ffmpeg.log'), 'w') do |log|
    Open3.popen3(*command) do |stdin, stdout, stderr, wait|
      stdin.close
      drainage = Thread.new { stderr.each_line { |line| log.write(line) } }
      begin
        while (bytes = stdout.read(64 * 36))
          raise 'incomplete grayscale frame' unless bytes.bytesize == 64 * 36
          windows.each { |w| w[:frames] << bytes if count.between?(w[:start], w[:finish]) }
          count += 1
          warn "Decoded #{count / 25} seconds of media" if (count % 7500).zero?
        end
      rescue Interrupt
        Process.kill('INT', wait.pid) rescue nil
        raise
      ensure
        stdout.close
      end
      drainage.join
      raise "FFmpeg failed: #{output}/ffmpeg.log" unless wait.value.success?
    end
  end
  end
  windows.each do |window|
    File.binwrite(File.join(output, format('window-%02d.gray', window[:id])), window[:frames].join)
  end
  cache_document = { source_signature: [source, File.size(source), File.mtime(source).to_f], decoded_frames: count,
                     windows: windows.map { |w| { id: w[:id], start: w[:start], finish: w[:finish] } } }
  File.write(File.join(output, 'window-cache.json'), JSON.pretty_generate(cache_document))
  results = windows.map do |window|
    warn "Refining candidate #{window[:id]}"
    descriptions = window[:frames].map { |bytes| describe_frame(bytes) }
    anchor_index = (window[:candidate].fetch('best_sample_seconds') * 25).round - window[:start]
    anchor = descriptions.fetch([[anchor_index, 0].max, descriptions.length - 1].min)
    flags = descriptions.map do |d|
      background_distance = d[:corner_means].zip(anchor[:corner_means]).map { |a, b| (a - b).abs }.max
      d[:graphic] && background_distance <= 30
    end
    # Bridge at most 0.2 s of animation blur; never bridge a black.
    seed_runs = contiguous_runs(flags)
    seed_runs.each_cons(2) do |left, right|
      gap = ((left[1] + 1)...right[0]).to_a
      if gap.length <= 5 && gap.none? { |i| descriptions[i][:black] }
        gap.each { |i| flags[i] = true }
      end
    end
    runs = contiguous_runs(flags)
    first = (window[:candidate].fetch('first_matching_sample_seconds') * 25).round - window[:start]
    last = (window[:candidate].fetch('last_matching_sample_seconds') * 25).round - window[:start]
    # Anchor only near already recognized PUB; do not search the reference montage.
    eligible = runs.select { |a, b| b - a + 1 >= 25 && b >= first - 12 && a <= last + 12 }
    row = { id: window[:id], coarse_candidate: window[:candidate], window_start_frame: window[:start],
            graphic_runs: runs.map { |a, b| [a + window[:start], b + window[:start]] } }
    if eligible.length != 1
      row.merge!(status: 'needs_review', reason: 'no unique smooth graphical run near PUB')
      next row
    end
    a, b = eligible.first
    start_frame = a + window[:start]
    end_exclusive = b + window[:start] + 1
    row[:separator_proposal] = { start_frame: start_frame, end_frame_exclusive: end_exclusive }
    # Six seconds before the selected PUB run: animation may split the jingle
    # into several smooth runs. This remains a provisional 6ter heuristic.
    blacks = contiguous_runs(descriptions.map { |d| d[:black] }).select do |left, right|
      right - left + 1 >= 2 && right < a && a - right <= 150
    end
    if a.zero? || b == window[:frames].length - 1
      row.merge!(status: 'needs_review', reason: 'graphical run touches sampled window edge')
    elsif !blacks.empty?
      black = blacks.last
      row.merge!(status: 'departure_hypothesis', boundary_frame: black[1] + window[:start] + 1,
                 boundary_method: 'first image after the last preceding black',
                 preceding_black: [black[0] + window[:start], black[1] + window[:start]])
    else
      row.merge!(status: 'return_hypothesis', boundary_frame: end_exclusive,
                 boundary_method: 'first image after the graphical run')
    end
    # Nine adjacent normalized images around each proposed graphical boundary.
    # Raw PGM inputs are retained only long enough to create each diagnostic sheet.
    directory = File.join(output, format('candidate-%02d', window[:id]))
    Dir.mkdir(directory)
    [[:start, a], [:end, b + 1], [:boundary, row[:boundary_frame] && row[:boundary_frame] - window[:start]]].each do |label, local_index|
      next unless local_index && local_index >= 4 && local_index + 4 < window[:frames].length
      frame_range = (local_index - 4)..(local_index + 4)
      inputs = frame_range.map { |i| "P5\n64 36\n255\n".b + window[:frames][i] }.join
      image_path = File.join(directory, "#{label}.png")
      args = ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error', '-f', 'image2pipe', '-vcodec', 'pgm', '-i', 'pipe:0',
              '-vf', 'scale=256:144:flags=neighbor,tile=9x1:padding=2', '-frames:v', '1', '-threads', '1', '-update', '1', '-n', image_path]
      _stdout, error, status = Open3.capture3(*args, stdin_data: inputs)
      row[:visual_error] = error unless status.success?
      row["#{label}_sheet_frames"] = frame_range.map { |i| i + window[:start] }
    end
    row
  end
  pairs = []
  pending = nil
  results.each do |row|
    if row[:status] == 'departure_hypothesis'
      pending = row
    elsif row[:status] == 'return_hypothesis' && pending
      length = row[:boundary_frame] - pending[:boundary_frame]
      if length.between?(60 * 25, 900 * 25)
        pairs << { status: 'unvalidated_hypothesis', departure_candidate: pending[:id], return_candidate: row[:id],
                   excluded_start_frame: pending[:boundary_frame], excluded_end_frame_inclusive: row[:boundary_frame] - 1,
                   duration_seconds: length.fdiv(25) }
      end
      pending = nil
    else
      pending = nil # An unresolved candidate prevents automatic bridging.
    end
  end
  report = { format: 'video_encoder.6ter_boundary_hypotheses', version: 3, source: source,
             elapsed_seconds: Process.clock_gettime(Process::CLOCK_MONOTONIC) - started,
             decoded_frames: count, decode_command: command, reused_cache: options[:reuse_cache], candidates: results, advertising_interval_hypotheses: pairs,
             limitations: [
               'Smooth outer-field classification is exploratory and can confuse graphic advertisements, overlays or scenes.',
               'A black within six seconds before the selected graphical run is evidence for departure, not proof; no black is not proof of programme return.',
               'Pairing uses sequence and a provisional duration range of 60..900 seconds; unresolved cases need review.',
               'No episode start/end is identified and no montage document is created or modified.',
               'Frame numbers use the reset full-decoded 25-fps clock. MLT equivalence was checked on Instinct only.',
               'Diagnostic sheets contain nine consecutive frames left-to-right; their absolute numbers are recorded.'
             ] }
  # Read the independent montage reference only AFTER every hypothesis is built.
  if options[:reference]
    corpus = JSON.parse(File.read(options[:reference]))
    matches = corpus.fetch('projects').select do |p|
      p.fetch('segments').map { |s| File.basename(s.fetch('source')) }.uniq == [File.basename(source)]
    end
    if matches.length == 1
      reference_segments = matches.first.fetch('segments')
      expected = reference_segments.each_cons(2).map do |left, right|
        { excluded_start_frame: left.fetch('end_frame') + 1, excluded_end_frame_inclusive: right.fetch('start_frame') - 1 }
      end
      # Direct local MLT images at each reference IN: independent of hypotheses.
      checks = []
      begin
        %w[video_export_profile mlt_project_builder].each do |name|
          require File.join(File.expand_path(options[:repo]), 'lib/video_encoder', name)
        end
        media = Struct.new(:path).new(Pathname(source))
        track = Struct.new(:index, :frame_rate).new(video.fetch('index'), Rational(25, 1))
        segment_class = Struct.new(:source, :start_frame, :end_frame)
        project_class = Struct.new(:segments)
        reference_segments.drop(1).each_with_index do |segment, index|
          frame = segment.fetch('start_frame')
          directory = File.join(output, "reference-return-#{index + 1}")
          Dir.mkdir(directory)
          xml = VideoEncoder::MltProjectBuilder.new.build(
            project_class.new([segment_class.new(media, frame - 4, frame + 4)]),
            audio_index: -1, video_tracks_by_source: { media => track }
          )
          xml_path = File.join(directory, 'reference.mlt')
          render_path = File.join(directory, 'reference.mkv')
          File.write(xml_path, xml)
          warn "Checking local MLT at reference return #{index + 1}"
          out, err, status = Open3.capture3({ 'QT_QPA_PLATFORM' => 'offscreen' },
            'melt-7', '-progress2', xml_path, '-consumer', "avformat:#{render_path}",
            'vcodec=ffv1', 'an=1', 'threads=2', 'real_time=-2', 'terminate_on_pause=1')
          File.write(File.join(directory, 'melt.log'), out + err)
          raise 'Short MLT render failed' unless status.success? && File.file?(render_path)
          probe_out, probe_err, probe_ok = Open3.capture3('ffprobe', '-v', 'error', '-count_frames',
            '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames', '-of', 'json', render_path)
          raise "Short MLT frame count failed: #{probe_err}" unless probe_ok.success?
          actual_count = JSON.parse(probe_out).fetch('streams').first.fetch('nb_read_frames').to_i
          raise "Expected 9 MLT frames, found #{actual_count}" unless actual_count == 9
          out, err, status = Open3.capture3('ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error',
            '-i', render_path, '-an', '-sn', '-dn', '-vf', 'scale=64:36,format=gray,scale=256:144:flags=neighbor,tile=9x1:padding=2',
            '-frames:v', '1', '-threads', '1', '-update', '1', '-n', File.join(directory, 'mlt.png'))
          raise "MLT sheet failed: #{err}" unless status.success?
          window = windows.find { |w| frame - 4 >= w[:start] && frame + 4 <= w[:start] + w[:frames].length - 1 }
          if window
            inputs = ((frame - 4)..(frame + 4)).map do |f|
              "P5\n64 36\n255\n".b + window[:frames].fetch(f - window[:start])
            end.join
            out, err, status = Open3.capture3('ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error',
              '-f', 'image2pipe', '-vcodec', 'pgm', '-i', 'pipe:0', '-vf', 'scale=256:144:flags=neighbor,tile=9x1:padding=2',
              '-frames:v', '1', '-threads', '1', '-update', '1', '-n', File.join(directory, 'full-decode.png'), stdin_data: inputs)
            raise "Full-decode sheet failed: #{err}" unless status.success?
          end
          checks << { reference_start_frame: frame, sheet_frames: ((frame - 4)..(frame + 4)).to_a,
                      reference_IN_sheet_index: 4, directory: directory, status: 'rendered_for_comparison' }
        end
      rescue StandardError => e
        checks << { status: 'failed', error: "#{e.class}: #{e.message}" }
      end
      report[:reference_mlt_visual_checks] = checks
      report[:reference_only_for_evaluation] = { project: matches.first.fetch('path'), expected_intervals: expected,
        comparisons: expected.map do |ref|
          nearest = pairs.min_by { |pair| (pair[:excluded_start_frame] - ref[:excluded_start_frame]).abs +
                                         (pair[:excluded_end_frame_inclusive] - ref[:excluded_end_frame_inclusive]).abs }
          { reference: ref, nearest_hypothesis: nearest, start_error_frames: nearest && nearest[:excluded_start_frame] - ref[:excluded_start_frame],
            end_error_frames: nearest && nearest[:excluded_end_frame_inclusive] - ref[:excluded_end_frame_inclusive] }
        end }
    else
      report[:reference_evaluation_error] = 'no unique matching reference project'
    end
  end
  report = AdSeparatorPairing.recover!(JSON.parse(JSON.generate(report)))
  File.write(File.join(output, 'boundary-hypotheses.json'), JSON.pretty_generate(report))
  warn "Finished: #{report.fetch('advertising_interval_hypotheses').length} interval hypotheses; #{output}/boundary-hypotheses.json"
rescue StandardError => e
  warn "#{e.class}: #{e.message}"
  exit 1
rescue Interrupt
  warn 'Interrupted; partial diagnostics retained.'
  exit 130
end
