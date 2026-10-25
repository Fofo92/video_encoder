# frozen_string_literal: true

require 'spec_helper'
require 'rbconfig'
require 'tmpdir'
require 'timeout'

RSpec.describe VideoEncoder::ParallelCommandRunner do
  around do |example|
    Dir.mktmpdir('parallel_audio') do |directory|
      @directory = directory
      example.run
    end
  end

  def path(name)
    File.join(@directory, name)
  end

  def command(name, script, *arguments)
    { argv: [RbConfig.ruby, '-e', script, *arguments], log_path: path("#{name}.log") }
  end

  def await_files(*files)
    Timeout.timeout(5) { sleep 0.01 until files.all? { |file| File.exist?(file) } }
  end

  def assert_reaped(pid_path)
    pid = Integer(File.read(pid_path))
    expect { Process.kill(0, pid) }.to raise_error(Errno::ESRCH)
    expect { Process.waitpid(pid, Process::WNOHANG) }.to raise_error(Errno::ECHILD)
  end

  it 'starts both commands before waiting and keeps their output separate' do
    script = <<~RUBY
      require 'timeout'
      File.write(ARGV[0], Process.pid)
      Timeout.timeout(5) { sleep 0.01 until File.exist?(ARGV[1]) }
      puts ARGV[2]
      warn ARGV[2]
    RUBY
    commands = [
      command('français &', script, path('french'), path('original'), 'français'),
      command('original', script, path('original'), path('french'), 'original')
    ]

    expect(described_class.new.run(commands)).to be(true)
    expect(File.read(commands[0][:log_path])).to eq("français\nfrançais\n")
    expect(File.read(commands[1][:log_path])).to eq("original\noriginal\n")
    assert_reaped(path('french'))
    assert_reaped(path('original'))
  end

  it 'never runs more than two commands at once' do
    script = 'File.write(ARGV[0], Process.pid); sleep 0.01 until File.exist?(ARGV[1])'
    commands = (1..3).map { |index| command(index, script, path(index.to_s), path('release')) }
    thread = Thread.new { described_class.new.run(commands) }
    thread.report_on_exception = false
    begin
      await_files(path('1'), path('2'))
      expect(File.exist?(path('3'))).to be(false)
      File.write(path('release'), '')
      expect(Timeout.timeout(5) { thread.value }).to be(true)
      (1..3).each { |index| assert_reaped(path(index.to_s)) }
    ensure
      thread.raise(Interrupt) if thread.alive?
      thread.join
    end
  end

  it 'terminates and reaps the other command when one command fails' do
    hanging = command('hanging', 'File.write(ARGV[0], Process.pid); sleep 60', path('pid'))
    failure = command('failure', <<~RUBY, path('pid'))
      require 'timeout'
      Timeout.timeout(5) { sleep 0.01 until File.exist?(ARGV[0]) }
      warn 'audio decoding failed'
      exit 7
    RUBY

    expect { described_class.new.run([hanging, failure]) }
      .to raise_error(VideoEncoder::CommandRunner::CommandFailed, /audio decoding failed/) do |error|
        expect(error.exit_status).to eq(7)
      end
    assert_reaped(path('pid'))
  end

  it 'reaps already started children if the next executable cannot start' do
    hanging = command('hanging', 'sleep 60')
    missing = { argv: [path('missing executable')], log_path: path('missing.log') }
    spawned = []
    allow(Process).to receive(:spawn).and_wrap_original do |method, *arguments, **options|
      method.call(*arguments, **options).tap { |pid| spawned << pid }
    end

    expect { described_class.new.run([hanging, missing]) }.to raise_error(Errno::ENOENT)
    spawned.each { |pid| expect { Process.kill(0, pid) }.to raise_error(Errno::ESRCH) }
  end

  it 'cleans up both children when the export is interrupted' do
    script = 'File.write(ARGV[0], Process.pid); sleep 60'
    commands = %w[french original].map { |name| command(name, script, path(name)) }
    thread = Thread.new { described_class.new.run(commands) }
    thread.report_on_exception = false
    begin
      await_files(path('french'), path('original'))
      thread.raise(Interrupt)
      expect { Timeout.timeout(5) { thread.value } }.to raise_error(Interrupt)
      assert_reaped(path('french'))
      assert_reaped(path('original'))
    ensure
      thread.raise(Interrupt) if thread.alive?
      begin
        thread.join
      rescue Interrupt
        nil
      end
    end
  end

  it 'honours the same process-group interruption used by the queue UI' do
    script = 'File.write(ARGV[0], Process.pid); sleep 60'
    commands = %w[french original].map { |name| command(name, script, path(name)) }
    worker = Process.fork do
      Signal.trap('INT', 'DEFAULT')
      Process.setpgrp
      begin
        described_class.new.run(commands)
      rescue Interrupt
        File.write(path('cancelled'), 'yes')
        exit! 0
      end
      exit! 1
    end
    begin
      await_files(path('french'), path('original'))
      Process.kill('INT', -worker)
      status = Timeout.timeout(5) { Process.waitpid2(worker).last }
      expect(status.success?).to be(true)
      expect(File.read(path('cancelled'))).to eq('yes')
      assert_reaped(path('french'))
      assert_reaped(path('original'))
    ensure
      begin
        Process.kill('KILL', -worker)
      rescue Errno::ESRCH
        nil
      end
      begin
        Process.waitpid(worker)
      rescue Errno::ECHILD
        nil
      end
    end
  end

  it 'uses KILL and reaps a child that ignores TERM' do
    stubborn = command('stubborn', 'trap("TERM") {}; File.write(ARGV[0], Process.pid); sleep 60', path('pid'))
    failure = command('failure', 'sleep 0.01 until File.exist?(ARGV[0]); exit 9', path('pid'))
    runner = described_class.new
    stub_const('VideoEncoder::ParallelCommandRunner::TERMINATION_SECONDS', 0.1)

    expect { runner.run([stubborn, failure]) }.to raise_error(VideoEncoder::CommandRunner::CommandFailed)
    assert_reaped(path('pid'))
  end

  it 'accepts an empty batch and rejects an unbounded concurrency setting' do
    expect(described_class.new.run([])).to be(true)
    expect { described_class.new.run([], limit: 3) }.to raise_error(ArgumentError)
  end
end
