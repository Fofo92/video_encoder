# frozen_string_literal: true

require_relative '../project_trash'

module VideoEncoder
  # Uses a fresh listing token for every confirmed destructive or restore action.
  class ProjectTrashCommand
    def initialize(argv:, database:)
      @argv = argv.dup
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
      return @trash.list if operation == 'list' && @argv.empty?
      return @trash.register(@argv.first) if operation == 'register' && @argv.one?
      return @trash.change(operation, *@argv) if %w[restore purge].include?(operation) && @argv.size == 2

      raise ArgumentError, 'Usage: project-trash [list | register ROOT | ' \
                           'restore DIRECTORY TOKEN | purge DIRECTORY TOKEN]'
    end
  end
end
