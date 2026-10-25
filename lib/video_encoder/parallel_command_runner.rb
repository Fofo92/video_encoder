# frozen_string_literal: true

module VideoEncoder
  # Runs a bounded batch of child processes and reaps all of them on failure.
  # Children stay in the export's process group so UI cancellation reaches them.
  class ParallelCommandRunner
    POLL_SECONDS = 0.02
    TERMINATION_SECONDS = 2.0

    def run(commands, limit: 2)
      raise ArgumentError, 'parallel limit must be 1 or 2' unless [1, 2].include?(limit)

      active = {}
      run_pending(commands.dup, active, limit)
      true
    ensure
      stop_children(active) if active
    end

    private

    def run_pending(pending, active, limit)
      until pending.empty? && active.empty?
        start_command(pending.shift, active) while !pending.empty? && active.length < limit
        reap_finished(active)
        sleep POLL_SECONDS unless active.empty?
      end
    end

    def start_command(command, active)
      # Interrupts must not arrive between spawning and registering a child.
      Thread.handle_interrupt(Interrupt => :never) do
        File.open(command.fetch(:log_path), 'wb') do |log|
          pid = Process.spawn(*command.fetch(:argv), out: log, err: log)
          active[pid] = command
        end
      end
    end

    def reap_finished(active)
      active.each_key do |pid|
        result = Process.waitpid2(pid, Process::WNOHANG)
        next unless result

        command = active.delete(pid)
        status = result.last
        next if status.success?

        error = CommandRunner::CommandFailed.new(command: command.fetch(:argv), status: status)
        raise error, "#{error.message}\n#{diagnostics(command)}"
      end
    end

    def diagnostics(command)
      path = command.fetch(:log_path)
      File.open(path, 'rb') do |log|
        log.seek([log.size - 4096, 0].max)
        "#{path}:\n#{log.read.force_encoding(Encoding::UTF_8).scrub}"
      end
    rescue SystemCallError
      "Audio diagnostics unavailable: #{path}"
    end

    def stop_children(active)
      Thread.handle_interrupt(Interrupt => :never) do
        signal_children(active, 'TERM')
        deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + TERMINATION_SECONDS
        while !active.empty? && Process.clock_gettime(Process::CLOCK_MONOTONIC) < deadline
          reap_stopped(active)
          sleep POLL_SECONDS unless active.empty?
        end
        signal_children(active, 'KILL')
        active.each_key do |pid|
          Process.waitpid(pid)
        rescue Errno::ECHILD
          nil
        end
        active.clear
      end
    end

    def signal_children(active, signal)
      active.each_key do |pid|
        Process.kill(signal, pid)
      rescue Errno::ESRCH
        nil
      end
    end

    def reap_stopped(active)
      active.each_key do |pid|
        active.delete(pid) if Process.waitpid(pid, Process::WNOHANG)
      rescue Errno::ECHILD
        active.delete(pid)
      end
    end
  end
end
