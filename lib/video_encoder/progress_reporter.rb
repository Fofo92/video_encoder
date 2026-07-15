
# frozen_string_literal: true

module VideoEncoder
  # Displays encoding progress on the terminal.
  class ProgressReporter
    BAR_WIDTH = 40

    def update(percent)
      percent = [[percent.to_i, 0].max, 100].min

      filled = BAR_WIDTH * percent / 100
      empty = BAR_WIDTH - filled

      bar = "#{'█' * filled}#{'░' * empty}"

      print "\r[#{bar}] #{format('%3d', percent)} %"
      $stdout.flush
    end

    def finish
      puts
    end
  end
end
