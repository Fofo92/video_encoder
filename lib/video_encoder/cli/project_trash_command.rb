# frozen_string_literal: true

require_relative '../project_trash'
require_relative '../project_trash_retention'

module VideoEncoder
  # Uses a fresh listing token for every confirmed destructive or restore action.
  class ProjectTrashCommand
    def initialize(argv:, database:)
      @argv = argv.dup
      @database = database
      @trash = ProjectTrash.new(database)
    end

    def run
      operation = @argv.shift || 'list'
      result = dispatch(operation)
      puts JSON.generate(result)
    rescue ProjectTrashError, ArgumentError, SystemCallError, JSON::ParserError, Sequel::DatabaseError => e
      abort(e.message)
    end

    private

    def dispatch(operation)
      return sweep if operation == 'sweep'
      return @trash.list if operation == 'list' && @argv.empty?
      return @trash.register(@argv.first) if operation == 'register' && @argv.one?
      return @trash.change(operation, *@argv) if %w[restore purge].include?(operation) && @argv.size == 2

      raise ArgumentError, 'Usage: project-trash [list | register ROOT | ' \
                           'restore DIRECTORY TOKEN | purge DIRECTORY TOKEN | sweep [--apply]]'
    end

    def sweep
      retention = ProjectTrashRetention.new(@database)
      return retention.sweep if @argv.empty?
      return retention.sweep(apply: true) if @argv == ['--apply']

      raise ArgumentError, 'Usage: project-trash sweep [--apply]'
    end
  end
end
