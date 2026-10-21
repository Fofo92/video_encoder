# Decoded-index review windows from temporal graphic groups

`script/research/prepare_overlay_review.py` takes a completed presence report and exterior programme times. It groups the graphic occurrences and selects the first and last occurrence in each candidate temporal group. These are candidate departure/resume observation locations, not accepted advertisement boundaries. Interior reviewed cut positions and an expected pause count are not inputs.

Sampled graphic times multiplied by 25 choose approximate centres for review windows only. Default windows extend 200 decoded frames on either side. Source identity must exactly match the presence report, and the source must have an average video rate of 25/1. One to six candidate groups are supported; unresolved graphics remain explicit in the grouping data. Overlapping windows are rejected.

```sh
python3 script/research/prepare_overlay_review.py \
  --latest-scan-for /path/to/recording.m2t \
  --programme-start 100 --programme-end 5000 \
  --output tmp/new-decoded-review
```

Alternatively supply `--report PATH`. Automatic report discovery searches `tmp` by default and ignores failed, incomplete, other-source and mismatched-identity reports. It does not restart a source scan. Output directory and sibling `.tar.gz` archive must not already exist.

FFmpeg reads the recording once. Each branch trims by decoded frame index **before** resetting timestamps. There is no frame-rate resampling filter before trimming. Output clips are encoded at 25 frames per second and 960 pixels wide. Each expected frame count and rate is checked, and every clip receives a SHA-256 digest. Source identity and report bytes are rechecked after extraction. The image-to-index map remains unverified against the editor until visually checked.

Progress comes from a separate observer of every 2,500th decoded input frame. Its counter is mapped back to the source index; output clip frame counts and local timestamps are not misreported as source progress. The observer ends at the last requested window. A real FFmpeg regression uses a frame-varying brightness counter to check the source-index phase in the exported clip and the progress counter after frame 2,500.

The archive contains the clips, `frame-map.json` and decoder log. The manifest records each first decoded index and exclusive end, approximate graphic position, grouping, source identity and report digest. Failed or interrupted extraction leaves diagnostics with explicit status and reaps the decoder. Reports are replaced atomically. The original recording, reviewed project, encoding workspace, application database and job queue are not modified.

A complete export is **not** a montage or proof of correct ad cuts. The actual jingle opening and closing still need refinement. Approximate source selection and verified exported frame count do not prove editor/source coordinate equivalence. These windows prepare visual review and subsequent measurement; they must not be silently converted into accepted timeline segments.
