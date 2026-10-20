# Motion and letterbox diagnostics on an existing cache

This is a research signal audit, not a new ad detector. It does not create a
project, infer advertising from aspect ratio, or change the discovery thresholds.

The audit reads the sealed 5 Hz RGB discovery cache, verifies its size and hash,
and measures both:

- motion-window eligibility at the current RMSE threshold of 2 and diagnostic
  thresholds of 1 and 0.5, summarized in one-minute regions;
- bilateral black bands, confirmed full-frame edges, unknown frames, stable
  episodes, and coarse transitions between episodes.

The image signal learns no channel colours or logo template. A row counts as
dark when at least 90% of its pixels have luminance at most 24/255 and luminance
standard deviation at most 4/255. Bands must appear at both edges, have similar
depths, leave active central content, and occupy at most one-third of the image
per edge. Full-frame evidence requires visible pixels at both edges. Entirely
dark frames remain unknown. States must last at least two seconds; unresolved
gaps longer than one second do not yield transition brackets.

These thresholds are exploratory. Dark scenes, overlays, framing changes within
a programme, and letterboxed advertisements can imitate or obscure this signal.
A transition is classified only as an unclassified format change. The tool
always requires review and never asserts that a recording contains no ads.

## Run without decoding the recording again

From the repository root:

```sh
python3 script/research/audit_capture_signals.py \
  --source /path/to/recording.m2t \
  --output tmp/capture-signal-audit.json
```

The source option selects a completed cache under `tmp`; it does not open the
recording. A particular cache can instead be supplied with `--cache DIRECTORY`.
A locally copied cache is preferred over an original absolute cache path, so
an archived cache can be audited offline. Its previously recorded hash is
mandatory. The original recording's current identity is not rechecked, and the
report states that limitation explicitly. The output path must not already
exist. Both the manifest and pixel checksum are checked again at the end.

The report contains local source provenance; review it before sharing. Times
belong to the resampled FFmpeg timeline, not verified editor frame indices.
At 5 Hz a transition bracket cannot establish an exact video-frame cut. A later
stage must inspect source images around a supported candidate.

Manual cut references are not accepted as inputs. They may be used afterwards
to assess coverage and locate failure causes. Real-capture validation remains
required before integrating either diagnostic signal into automatic decisions.
