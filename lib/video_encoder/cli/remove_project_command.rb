# frozen_string_literal: true

require 'optparse'
require_relative '../project_removal'

module VideoEncoder
  # Exposes a preview followed by a separately confirmed recoverable removal.
  class RemoveProjectCommand
    def initialize(argv:, database:)
      @argv = argv.dup
      @database = database
    end

    def run
      options = {}
      OptionParser.new do |parser|
        parser.on('--dependencies') { options[:dependencies] = true }
        parser.on('--confirm TOKEN') { |value| options[:token] = value }
      end.parse!(@argv)
      raise ArgumentError, 'Usage: remove-project PROJECT.json [--dependencies] [--confirm TOKEN]' unless @argv.one?

      puts JSON.generate(ProjectRemoval.new(@database).call(@argv.first, **options))
    rescue ProjectRemovalError, ArgumentError, KeyError, TypeError, OptionParser::ParseError,
           SystemCallError, JSON::ParserError, Sequel::DatabaseError => e
      abort(e.message)
    end
  end
end
