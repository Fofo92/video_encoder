# frozen_string_literal: true

require 'open3'
require 'json'
require 'English'

module VideoEncoder
  module AdDetection
    # Runs a detector in its own directory without invoking a shell or an encoder.
    class ComskipExecution
      def initialize(executable: ENV.fetch('VIDEO_ENCODER_COMSKIP', 'comskip'))
        @executable = executable
      end

      def version
        stdout, stderr, status = Open3.capture3(@executable, '--help')
        raise "Comskip unavailable: #{stderr}" unless [0, 1, 2].include?(status.exitstatus)

        line = (stdout + stderr).lines.grep(/\AComskip \d/).first
        raise 'Comskip did not report its version' unless line

        line.strip
      rescue Errno::ENOENT
        raise 'Comskip is not installed. Install the comskip package before running this evaluation.'
      end

      def frame_rate(source)
        stdout, stderr, status = Open3.capture3(
          'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
          'stream=avg_frame_rate', '-of', 'json', source
        )
        raise "FFprobe failed: #{stderr}" unless status.success?

        Rational(JSON.parse(stdout).fetch('streams').first.fetch('avg_frame_rate'))
      end

      def call(source, workspace)
        command = [@executable, "--ini=#{workspace}/comskip.ini", "--output=#{workspace}",
                   '--output-filename=analysis', '--threads=2', source]
        success = system(*command, chdir: workspace, out: "#{workspace}/console.log", err: %i[child out])
        code = $CHILD_STATUS&.exitstatus
        return if success || code == 1

        raise "Comskip failed (#{code}); diagnostics retained in #{workspace}"
      end
    end
  end
end
