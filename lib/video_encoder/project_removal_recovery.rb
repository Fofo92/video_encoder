# frozen_string_literal: true

require 'fileutils'
require 'securerandom'

module VideoEncoder
  # Holds removed files and an explicit restoration manifest on the same volume.
  class ProjectRemovalRecovery
    def call(project, files)
      directory = recovery_directory(project)
      entries = files.each_with_index.map do |file, index|
        [file, File.join(directory, "#{index}-#{File.basename(file)}")]
      end
      File.write(File.join(directory, 'manifest.json'), JSON.pretty_generate(entries.to_h))
      yield directory if block_given?
      move_entries(entries)
      directory
    end

    private

    def recovery_directory(project)
      root = File.join(File.dirname(project), '.video_encoder_trash')
      raise ProjectRemovalError, 'Le dossier de récupération est un lien symbolique.' if File.symlink?(root)

      FileUtils.mkdir_p(root, mode: 0o700)
      directory = File.join(root, SecureRandom.uuid)
      Dir.mkdir(directory, 0o700)
      directory
    end

    def move_entries(entries)
      moved = []
      begin
        entries.each do |source, target|
          File.rename(source, target)
          moved << [source, target]
        end
      rescue StandardError
        moved.reverse_each { |source, target| File.rename(target, source) }
        raise
      end
    end
  end
end
