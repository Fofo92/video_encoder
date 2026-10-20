# Observation-learned graphic scan over a full recording

`script/research/scan_stable_overlays.py` learns a shared near-white graphic from two to six distinct observation clips, then reads one recording once in a bounded stream. It is an experimental presence scan, **not blind discovery, separator classification or automatic cutting**. The observations can have been selected around known junctions; scanning the rest of the recording checks additional matches but does not constitute an independent recording test.

```sh
python3 script/research/scan_stable_overlays.py \
  --source /path/to/recording.m2t \
  --clips tmp/observations/one.mp4 tmp/observations/two.mp4 tmp/observations/three.mp4 \
  --output tmp/new-overlay-scan
```

FFmpeg, FFprobe and NumPy are required. This pilot requires square-pixel 16:9 video. Every observation is limited to 300 samples (60 seconds at five samples per second); the recording is limited to 108,000 samples (six hours). Oversized input causes a failed report, never a successful partial scan.

Learning uses the largest shared white-edge region and refines its concurrent support across observations. Before reading the recording, the learned graphic must pass the same sustained-presence threshold in each training observation; otherwise the run fails. This training check is not an independent accuracy test. It searches only that unclassified graphic, so other separator families can be missed. No reference project, desired cut positions, hand-selected spatial box or preinstalled channel template is accepted. It does not verify that each observation came from this particular recording; the report explicitly records that limitation.

The source scan scales samples to 640×360 and transfers only a padded learned region through the RGB pipe. RGB conversion precedes cropping to preserve odd crop coordinates. Samples are processed in blocks of 100. Graphic intervals can cross block boundaries; a final short block is padded only for image operations, without counting artificial samples. The full sampled recording is never cached on disk. Memory is bounded, though learning retains the short observations; use short clips rather than the maximum permitted lengths.

The new output directory contains `report.json`, a small learned-mask archive and decoder logs. It must not already exist. Progress shows analysed recording time and real elapsed time. Completed reports require successful decoder termination, unchanged source identity and unchanged observation identity and SHA-256 hashes. Report updates replace the JSON atomically. Failed or interrupted runs retain explicit status and diagnostics; they do not resume decoding from that point. Termination reaps the decoder process. No capture, project, workspace, database or encoding job is changed.

Report intervals describe samples whose graphic-presence score is at least 0.8 for at least three consecutive samples. Scores are not calibrated probabilities. Times use FFmpeg’s `fps=5:start_time=0` timeline, not verified original decoded/editor frame indices. A graphic can appear late in a jingle; these intervals must not be used as ad cuts or accepted montage segments.

Review all occurrences over the recording, including outside the programme bounds, before considering any subsequent integration. Synthetic streaming tests and a held-out observation check establish implementation behaviour, not production accuracy on a whole recording.
