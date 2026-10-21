# Integrated observation-assisted raccord preparation

`script/research/prepare_graphic_review.py` runs the research stages in one invocation: learn graphic hypotheses, scan the source once, group occurrences within the exterior programme bounds, extract native review clips, and propose raccord candidates. It requires a 25 fps source and two to six existing observation clips. It does not discover a separator directly from the source alone.

## UI entry

Open **Séparateurs répétés (expérimental)…** after setting the exterior IN and OUT. In simplified mode, **Préparer les raccords à contrôler** uses existing compatible extraction clips automatically when available; it does not ask for a detector, family or directory. A normal failed legacy refinement can also continue once through this graphic path when complete observation clips exist. A graphic failure does not restart itself.

The UI locates extraction manifests for the unchanged source. Only complete windows lying inside the current exterior bounds are eligible. Adjusting exterior bounds does not invalidate observation pixels that still fit; results and accepted segment geometry remain tied to the exact current bounds. The child worker checks local file paths, frame counts, 25 fps timing, available hashes and source identity before learning. Truncated legacy containers are rejected rather than silently assigned valid frame maps.

Four stage labels, elapsed wall time and actual sampled-video/source-frame progress are displayed while the process runs. Completed candidates show the last kept/first discarded frame at departures and last discarded/first kept frame at resumes. Reopening a result does not rerun the calculation or restore semantic confirmation. A partial result can show individual candidate previews but cannot replace the montage. Source identity and exterior bounds are checked again before a confirmed result is loaded. Encoding is still a separate action.

For a new source without compatible observations, the existing discovery/refinement path remains in use. This integration does not establish a universal source-only advertising detector.

## Research command

```sh
python3 script/research/prepare_graphic_review.py \
  --source '/path/to/recording.m2t' \
  --clips '/path/to/observation-1.mp4' '/path/to/observation-2.mp4' \
  --in-frame 1000 --out-frame 100000 \
  --output 'tmp/graphic-review-new-run'
```

IN and OUT are exterior frame indices at 25 fps; OUT is inclusive. No reviewed interior cut is an input. Observation clips must have a compatible picture geometry; their extraction still introduces selection bias. Sampled timestamps and decoded source indices do not establish editor alignment.

Instead of `--clips`, `--observation-manifest /path/to/manifest.json` uses the same validated extraction-selection path as the UI. Its identity is retained in the pipeline report. Window metadata selects observation pixels; reviewed motif limits and interior cut coordinates are not learner inputs.

The caller does not choose white versus contrast evidence. Both hypotheses are attempted. An expected training abstention is retained in `scan/report.json`; another valid hypothesis can continue. If both fail, the run fails explicitly. The recording is decoded once into the bounding crop covering the learned regions, with bounded blocks. Each hypothesis keeps separate streaming state across block boundaries.

Overlapping sampled detections are united once, preserving every contributing occurrence and its edge mode. Disjoint or merely touching detections remain separate; no gap is filled. A signal found by only one method is retained and marked for review. Related image tests are not counted as independent confirmations or converted into a confidence probability. The individual lists remain in `occurrences_by_hypothesis`.

The output directory must be new. `pipeline.json` records the current stage, elapsed time, diagnostic paths and final state atomically:

| State | Meaning |
| --- | --- |
| `ready_for_review` | Each candidate group has paired raccord candidates, with no unresolved temporal groups or straddling graphics. Human review remains necessary. |
| `needs_review` | Grouping, window preparation or a raccord remains unresolved. The available diagnostics are retained. An empty list is not proof that the programme has no advertisements. |
| `failed` | A technical error stopped subsequent stages. The failing stage and error are recorded. |
| `interrupted` | The run was interrupted. Available reports and clips remain for diagnosis. |

The scanner rechecks the source and observation identities. Extraction requires the completed scan's source identity; native clips carry frame counts and checksums, which refinement verifies. Existing output directories are not overwritten. Interrupted runs do not implicitly resume or reuse an incomplete report.

`groups.json`, `raccords/frame-map.json`, `raccords.tar.gz` and `raccords.json` are produced as their stages complete. Candidate kept frames are never written as an accepted project or submitted to the encoding queue. Graphic presence does not establish complete jingle bounds, and a strong transition may be a shot inside the programme or an advertisement.

## Validation

A real FFmpeg integration test generates a recording with two opposite-polarity graphics separated in time, extracts observations, and runs the complete pipeline through the extraction-manifest option used by the UI. It verifies temporal grouping, native extraction, the last-kept/first-kept conventions, retained manual-review status and an unchanged source digest. Synthetic reference positions are compared only after inference. Additional tests cover dual streaming with different crops and block boundaries, overlapping provenance without duplicate occurrences, single-hypothesis fallback, both-hypothesis failure, empty grouping and interruption/error stop conditions. Qt tests cover automatic launch without group selection, real child-process completion, partial and empty results, exact adjacent preview frames, confirmation, four-stage progress and reopening. Clip-count, hash and escaping-path checks run against real FFmpeg-produced observations.

The opening-transition search includes the anchor's first graphic frame: a jingle can begin exactly there. It does not search after that frame. This fixes a case exposed by the integration test; it is not a claim that all graphic starts are valid cuts.
