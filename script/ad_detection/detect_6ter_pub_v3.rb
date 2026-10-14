#!/usr/bin/env ruby
# frozen_string_literal: true

# Exploratory 6ter PUB-screen detection, not a commercial-removal tool.
# Reference edge templates are embedded below. No montage JSON is read.
require 'json'
require 'open3'
require 'optparse'
require 'base64'
require 'zlib'

def edge_vector(bytes, dx = 0, dy = 0)
  pixels = bytes.unpack('C*')
  vector = []
  # Central 32x14 region at x=16,y=12 in the normalized 64x36 image.
  # Horizontal differences, then vertical differences, in row-major order.
  ((12 + dy)...(26 + dy)).each do |y|
    ((16 + dx)...(47 + dx)).each { |x| vector << pixels[y * 64 + x + 1] - pixels[y * 64 + x] }
  end
  ((12 + dy)...(25 + dy)).each do |y|
    ((16 + dx)...(48 + dx)).each { |x| vector << pixels[(y + 1) * 64 + x] - pixels[y * 64 + x] }
  end
  norm = Math.sqrt(vector.sum { |value| value * value })
  return nil if norm < 1.0

  vector.map { |value| value / norm }
end

options = { threshold: 0.75, start_seconds: nil, duration_seconds: nil }
OptionParser.new do |p|
  p.banner = 'Usage: ruby detect_6ter_pub_v3.rb --source CAPTURE --output NEW_DIRECTORY [--threshold SCORE] [--start SECONDS --duration SECONDS]'
  p.on('--source PATH') { |v| options[:source] = v }
  p.on('--output PATH') { |v| options[:output] = v }
  p.on('--start SECONDS', Float) { |v| options[:start_seconds] = v }
  p.on('--duration SECONDS', Float) { |v| options[:duration_seconds] = v }
  p.on('--threshold NUMBER', Float) { |v| options[:threshold] = v }
end.parse!

begin
  unless options[:source] && options[:output] && ARGV.empty? && File.file?(options[:source])
    raise ArgumentError, '--source existing file and --output new directory required; no positional arguments'
  end
  raise ArgumentError, 'threshold must be between 0 and 1' unless options[:threshold] > 0 && options[:threshold] <= 1

  raise ArgumentError, 'start must be non-negative' if options[:start_seconds] && options[:start_seconds] < 0
  raise ArgumentError, 'duration must be positive' if options[:duration_seconds] && options[:duration_seconds] <= 0

  templates = JSON.parse(Zlib::Inflate.inflate(Base64.decode64(DATA.read)))
  output = File.expand_path(options[:output])
  source = File.expand_path(options[:source])
  Dir.mkdir(output)
  command = ['ffmpeg', '-hide_banner', '-nostdin', '-nostats', '-loglevel', 'warning',
             '-threads', '2', '-i', source, '-map', '0:v:0', '-an', '-sn', '-dn',
             '-filter_threads', '1', '-vf', 'setpts=PTS-STARTPTS,scale=64:36,format=gray,fps=2:start_time=0',
             '-fps_mode', 'passthrough', '-threads', '1', '-f', 'rawvideo', 'pipe:1']
  if options[:start_seconds]
    command.insert(command.index('-i'), '-ss', format('%.6f', options[:start_seconds]))
  end
  if options[:duration_seconds]
    command.insert(command.index('-filter_threads'), '-t', format('%.6f', options[:duration_seconds]))
  end
  samples = 0
  events = []
  hits = 0
  started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  status = nil
  warn "Scanning #{source}; no montage references are used."
  File.open(File.join(output, 'ffmpeg.log'), 'w') do |log|
    Open3.popen3(*command) do |stdin, stdout, stderr, wait|
      stdin.close
      drainage = Thread.new { stderr.each_line { |line| log.write(line) } }
      begin
        while (bytes = stdout.read(64 * 36))
          raise 'incomplete grayscale frame' unless bytes.bytesize == 64 * 36
          vector = edge_vector(bytes)
          if vector
            best = templates.map do |template|
              score = 0.0
              template.fetch('vector').each_with_index { |value, i| score += value * vector[i] }
              [template.fetch('id'), score]
            end.max_by { |_name, score| score }
            best_shift = [0, 0]
            # Retry only moderately similar frames; keep the recognition threshold.
            if best[1] >= 0.25 && best[1] < options[:threshold]
              [-1, 0, 1].each do |dy|
                [-1, 0, 1].each do |dx|
                  next if dx.zero? && dy.zero?
                  shifted = edge_vector(bytes, dx, dy)
                  next unless shifted
                  templates.each do |template|
                    score = 0.0
                    template.fetch('vector').each_with_index { |value, i| score += value * shifted[i] }
                    if score > best[1]
                      best = [template.fetch('id'), score]
                      best_shift = [dx, dy]
                    end
                  end
                end
              end
            end
            if best[1] >= options[:threshold]
              seconds = samples.fdiv(2) + (options[:start_seconds] || 0)
              hits += 1
              event = events.last
              if event && seconds - event[:last_matching_sample_seconds] <= 0.75
                event[:last_matching_sample_seconds] = seconds
                event[:matching_samples] += 1
              else
                event = { first_matching_sample_seconds: seconds, last_matching_sample_seconds: seconds,
                          matching_samples: 1, best_score: best[1], best_sample_seconds: seconds, best_template: best[0], best_template_shift_pixels: best_shift }
                events << event
              end
              if best[1] > event[:best_score]
                event[:best_score] = best[1]
                event[:best_sample_seconds] = seconds
                event[:best_template] = best[0]
                event[:best_template_shift_pixels] = best_shift
              end
              warn "PUB candidate at #{format('%.2f', seconds)} s, score #{format('%.3f', best[1])}"
            end
          end
          samples += 1
          warn "Analysed approximately #{samples / 2} seconds of media" if (samples % 600).zero?
        end
      rescue Interrupt
        Process.kill('INT', wait.pid) rescue nil
        raise
      ensure
        stdout.close
      end
      drainage.join
      status = wait.value
    end
  end
  report = {
    format: 'video_encoder.6ter_pub_candidates', version: 3,
    source: source, complete: status.success?, ffmpeg_exit_status: status.exitstatus,
    elapsed_seconds: Process.clock_gettime(Process::CLOCK_MONOTONIC) - started,
    command: command, sample_rate: '2/1', analysed_samples: samples,
    template_count: templates.length, translation_tolerance_pixels: 1, translation_retry_min_score: 0.25, requested_start_seconds: options[:start_seconds], requested_duration_seconds: options[:duration_seconds],
    timestamp_clock: options[:start_seconds] ? 'seek-relative plus requested start; approximate, not validated for cuts' : 'reset full-decoded-video PTS at 2 fps',
    threshold: options[:threshold], matching_samples: hits, candidate_count: events.length, candidates: events,
    calibration: 'Seven manually observed PUB images: six initial references plus the missed pale-pink PUB screen in Survivors S04 E14, normalized central grayscale gradients. Initial exploratory threshold 0.75.',
    limitations: [
      'Candidates are PUB-screen appearances, not advertisement intervals or cuts.',
      'Scan includes recording margins and adjacent programmes; do not force a limit of four screens.',
      'Sample timestamps use the reset full-decoded-video clock at 2 fps; uncertainty is at least the 0.5-second sampling step.',
      'No entry/exit direction is inferred and no source, project or queue is modified.',
      'Instinct, Dans le noir, Survivors and now Treasure Hunt have influenced calibration or position-tolerance rules. Test a new capture with frozen templates and settings.',
      'When --start is used, timestamps are approximate seek-based positions; do not use them as montage bounds.',
      'Profile covers observed 6ter PUB screens; it is not an M6 or TF1 detector.',
      'One matching sample remains an unconfirmed candidate requiring inspection.'
    ]
  }
  File.write(File.join(output, 'pub-candidates.json'), JSON.pretty_generate(report))
  warn "Finished: #{events.length} candidates; #{output}/pub-candidates.json"
  exit(status.success? ? 0 : 2)
rescue StandardError => e
  warn "#{e.class}: #{e.message}"
  exit 1
rescue Interrupt
  warn 'Interrupted; partial FFmpeg log retained.'
  exit 130
end

__END__
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
gPWzpXVM4mu7msZy//bvv/0flO/uWw==
