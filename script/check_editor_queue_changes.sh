#!/usr/bin/env bash
set -euo pipefail

queue_project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$queue_project_root"

bundle exec rspec \
  spec/persistence/job_repository_spec.rb \
  spec/persistence/job_repository_queue_actions_spec.rb \
  spec/trim_export_worker_spec.rb \
  spec/trim_export_worker_queue_race_spec.rb \
  spec/cli/manage_trim_job_command_spec.rb \
  spec/active_trim_export_deferred_usage_spec.rb

for queue_test_pattern in \
  'test_trim_export_queue*.py' \
  'test_queue_usability.py' \
  'test_application_marker_nudge.py' \
  'test_application_segment_editing.py' \
  'test_application_audio_preflight.py' \
  'test_widgets.py' \
  'test_trim_project_archiver*.py'
do
  PYTHONPATH=ui QT_QPA_PLATFORM=offscreen python3 -m unittest discover \
    -s ui/tests -p "$queue_test_pattern"
done
