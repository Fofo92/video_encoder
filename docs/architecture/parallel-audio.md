# Parallel audio export

The video render and subtitle extraction retain their existing order. Once the
subtitle policy has selected the retained audio roles, French and original audio
are rendered concurrently, with at most two child processes. A single retained
track is rendered normally. Whole queue jobs are still processed sequentially.

Each audio role uses its own `audio_french.mlt` or `audio_original.mlt`. The video
track must remain disabled (`video_index=-1`), including when video metadata is
provided to convert frame boundaries. Install the audio-only builder correction
before this change. AAC, 160 kbit/s, segment bounds and final stream order are
unchanged. Original audio omitted by the subtitle policy is not restored.

The remux starts only after all required audio renders have succeeded and their
outputs are nonempty. Children remain in the worker process group for existing
UI cancellation. On failure, spawn error or Ruby interruption, the batch runner
terminates and reaps remaining children, escalating from TERM to KILL after two
seconds. Per-track stdout and stderr go into workspace `.mka.log` files, preventing
conflicting percentage updates. The failure message includes the failing log's
last 4 KiB. Workspaces, including diagnostic logs, are removed after success by
the existing cleanup service; unsuccessful workspaces remain available.

The editor and queue display **Audio français + original (parallèle)**. The editor
uses an activity indicator rather than mixing percentages from two processes.
The per-track progress display is retained for a single track or serial mode.

## Measurements

The existing `<output>.video_encoder-export.json` receipt gains an optional
`timings` array. Each entry records `stage`, monotonic wall time in
`elapsed_seconds`, and `status`. Stages are video, subtitles, audio and remux;
audio also records the retained `roles` and effective `concurrency`. No extra
report file is created. Durations exclude project loading, initial probing,
workspace cleanup and receipt generation. With no subtitle exporter, its timing
entry measures the empty preparation step. There is no receipt for a failed
export, as before.

Default concurrency is two. For a sequential comparison, close the idle UI and
start it from a terminal with:

```bash
VIDEO_ENCODER_AUDIO_CONCURRENCY=1 bin/video_encoder_ui
```

Alternatively run a project directly with a distinct output filename:

```bash
VIDEO_ENCODER_AUDIO_CONCURRENCY=1 bin/video_encoder export /path/project.json --output /path/comparison-serial.mkv
VIDEO_ENCODER_AUDIO_CONCURRENCY=2 bin/video_encoder export /path/project.json --output /path/comparison-parallel.mkv
```

Only values 1 and 2 are accepted. Both modes use the same audio projects, codec,
bitrate and cut bounds. Compare the audio stage's wall time for the **same project
and source**, with no other encodes running; different films or track counts do
not establish a speedup. Source cache state can affect measurements. The
parallel audio duration is the elapsed time for the batch, not the sum of each
track's CPU time. Confirm the rendered output before adopting the measured gain.

The optional receipt field does not change its format/version or required fields.
Existing receipts without timings remain valid. No database schema change is
required and no change is made to the video encoder preset or hardware choice.
