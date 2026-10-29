# frozen_string_literal: true

require 'optparse'

module VideoEncoder
  # The preview and execution use the same file and queue checks.
  class MoveProjectCommand
    def initialize(argv:, database:)
      @argv = argv.dup
      @database = database
    end

    def run
      options = {}
      parser = OptionParser.new do |item|
        item.on('--directory DIRECTORY') { |value| options[:directory] = value }
        item.on('--name NAME') { |value| options[:name] = value }
        item.on('--preview') { options[:preview] = true }
      end
      parser.parse!(@argv)
      raise ArgumentError, 'Usage: move-project PROJECT.json --directory FOLDER [--name NAME] [--preview]' unless
        @argv.one? && options[:directory]

      result = ProjectRelocation.new(@database).call(@argv.first, options.delete(:directory), **options)
      puts(options[:preview] ? JSON.generate(result) : result)
    rescue ProjectRelocationError, ArgumentError, OptionParser::ParseError, SystemCallError,
           JSON::ParserError, Sequel::DatabaseError => e
      abort(e.message)
    end
  end
end
