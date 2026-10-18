# frozen_string_literal: true

require 'json'
require 'digest'
require 'time'
require 'fileutils'
require_relative 'comskip_coordinates'

module VideoEncoder
  module AdDetection
    # Stores a reusable observation separately from editable montage proposals.
    class ComskipAnalysis
      def initialize(profile:, execution: ComskipExecution.new)
        @profile = File.binread(profile)
        @execution = execution
      end

      def call(source:, workspace:, recover_complete_output: false)
        source = File.realpath(source)
        raise ArgumentError, 'Source must be a regular file' unless File.file?(source)

        workspace = File.expand_path(workspace)
        raise ArgumentError, 'Workspace cannot be a symlink' if File.symlink?(workspace)

        identity = identity_for(source)
        if recover_complete_output && File.directory?(workspace) && !File.exist?("#{workspace}/analysis.json")
          return recover(source, workspace, identity)
        end
        return reuse(source, workspace, identity) if File.exist?(workspace)

        execute(source, workspace, identity)
      end

      private

      def identity_for(source)
        stat = File.stat(source)
        { 'source' => source, 'device' => stat.dev, 'inode' => stat.ino, 'bytes' => stat.size,
          'mtime_ns' => (stat.mtime.to_r * 1_000_000_000).to_i,
          'ctime_ns' => (stat.ctime.to_r * 1_000_000_000).to_i,
          'profile_sha256' => Digest::SHA256.hexdigest(@profile), 'engine' => @execution.version }
      end

      def execute(source, workspace, identity)
        rate = @execution.frame_rate(source)
        raise ArgumentError, 'Source has no usable average frame rate' unless rate.positive?

        FileUtils.mkdir_p(File.dirname(workspace))
        Dir.mkdir(workspace)
        File.write("#{workspace}/comskip.ini", @profile)
        write_json("#{workspace}/request.json", identity)
        started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
        @execution.call(source, workspace)
        raise 'Source changed during analysis' unless identity_for(source) == identity

        finish(workspace, identity, read_cuts(workspace), rate,
               Process.clock_gettime(Process::CLOCK_MONOTONIC) - started)
      end

      def finish(workspace, identity, native, rate, elapsed, recovered: false)
        cuts = ComskipCoordinates.convert(native, rate)
        report = { 'format' => 'video_encoder.comskip_analysis', 'version' => 1,
                   'status' => 'complete', 'identity' => identity,
                   'cut_list_sha256' => Digest::SHA256.file("#{workspace}/analysis.txt").hexdigest,
                   'elapsed_seconds' => elapsed, 'recovered_output' => recovered,
                   'native_frame_rate' => native.frame_rate.to_s, 'native_frame_count' => native.frame_count,
                   'scanned_frame_count' => cuts.frame_count, 'frame_rate' => cuts.frame_rate.to_s,
                   'excluded_intervals' => cuts.intervals, 'needs_manual_review' => true }
        write_json("#{workspace}/analysis.json", report)
        [cuts, report, false]
      end

      def recover(source, workspace, identity)
        request = JSON.parse(File.read("#{workspace}/request.json"))
        profile = Digest::SHA256.file("#{workspace}/comskip.ini").hexdigest
        unless request == identity && profile == identity.fetch('profile_sha256')
          raise ArgumentError, 'Cannot recover output: source, engine or profile has changed'
        end

        native = read_cuts(workspace)
        rate = @execution.frame_rate(source)
        raise 'Source changed during recovery' unless identity_for(source) == identity

        # Explicit recovery accepts a complete TXT after an interrupted adapter;
        # it does not invent an engine exit status or a measured runtime.
        cuts, report, = finish(workspace, identity, native, rate, nil, recovered: true)
        [cuts, report, true]
      end

      def reuse(source, workspace, identity)
        report = JSON.parse(File.read("#{workspace}/analysis.json"))
        valid = report['format'] == 'video_encoder.comskip_analysis' && report['version'] == 1 &&
                report['status'] == 'complete' && report['identity'] == identity &&
                Digest::SHA256.file("#{workspace}/analysis.txt").hexdigest == report['cut_list_sha256']
        raise ArgumentError, "Analysis does not match #{source}; keep it and choose a new workspace" unless valid

        [ComskipCoordinates.convert(read_cuts(workspace), Rational(report.fetch('frame_rate'))), report, true]
      end

      def read_cuts(workspace)
        ComskipCutList.new(File.read("#{workspace}/analysis.txt"))
      end

      def write_json(path, document)
        File.open(path, File::WRONLY | File::CREAT | File::EXCL) { |file| file.write("#{JSON.pretty_generate(document)}\n") }
      end
    end
  end
end
