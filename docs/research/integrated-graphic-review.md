# Integrated observation-assisted raccord preparation

`script/research/prepare_graphic_review.py` runs the research stages in one invocation: learn graphic hypotheses, scan the source once, group occurrences within the exterior programme bounds, extract native review clips, and propose raccord candidates. It requires a 25 fps source and either existing observations or a compatible initial discovery report. The discovery route can prepare initial observations automatically; none of its proposals are verified separators.

## UI entry

Open **Séparateurs répétés (expérimental)…** after setting the exterior IN and OUT. In simplified mode, **Préparer les raccords à contrôler** uses existing compatible extraction clips automatically when available; it does not ask for a detector, family or directory. A normal failed legacy refinement can also continue once through this graphic path when complete observation clips exist. A graphic failure does not restart itself.

The UI locates extraction manifests for the unchanged source. Only complete windows lying inside the current exterior bounds are eligible. Adjusting exterior bounds does not invalidate observation pixels that still fit; results and accepted segment geometry remain tied to the exact current bounds. The child worker checks local file paths, frame counts, 25 fps timing, available hashes and source identity before learning. Truncated legacy containers are rejected rather than silently assigned valid frame maps.

Four or five stage labels, elapsed wall time and actual sampled-video/source-frame progress are displayed while the process runs. Completed candidates show the last kept/first discarded frame at departures and last discarded/first kept frame at resumes. Reopening a result does not rerun the calculation or restore semantic confirmation. A partial result can show individual candidate previews but cannot replace the montage. Source identity and exterior bounds are checked again before a confirmed result is loaded. Encoding is still a separate action.

For a new source without compatible observations, a missing or tied family hypothesis can now prepare observations from the initial discovery pool. The simplified button remains usable instead of requiring a technical family choice. This integration does not establish universal advertisement accuracy.

## Initial observations without a selected family

The discovery route pools all reported cores, unites overlapping core intervals with candidate provenance, and applies the same bounded temporal clustering used by the graphic grouping stage. It does not rank tied families or convert a scenario into cuts. One to three viable zones provide two context clips each; isolated, short, overlong and boundary-straddling evidence stays in the grouping diagnostics. More than three viable zones or overlapping windows stays unresolved rather than silently dropping zones.

Each context extends at most 20 seconds before and after a zone endpoint, clamped to the exterior programme bounds. Indices only plan approximate context windows. Native extraction verifies frame counts, cadence, hashes and source identity before the pixels can teach either graphic model. The complete discovery pool and partial-search flag remain identifiable. There are five visible stages, starting with observation extraction. Completed observation exports can be reused after a later failure.

These initial observations are automatically selected from unclassified proposals, without interior reference cuts. They can contain repeated advertisements or programme graphics rather than jingles. A successful graphic match or grouping does not validate advertising semantics or complete coverage.

## Research command

```sh
python3 script/research/prepare_graphic_review.py \
  --source '/path/to/recording.m2t' \
  --clips '/path/to/observation-1.mp4' '/path/to/observation-2.mp4' \
  --in-frame 1000 --out-frame 100000 \
  --output 'tmp/graphic-review-new-run'
```

IN and OUT are exterior frame indices at 25 fps; OUT is inclusive. No reviewed interior cut is an input. Observation clips must have a compatible picture geometry; their extraction still introduces selection bias. Sampled timestamps and decoded source indices do not establish editor alignment.

Instead of `--clips`, `--discovery-report /path/to/resultat.json` prepares initial observations from the entire pool. Alternatively, `--observation-manifest /path/to/manifest.json` uses the same validated extraction-selection path as the UI. Its identity is retained in the pipeline report. Window metadata selects observation pixels; reviewed motif limits and interior cut coordinates are not learner inputs.

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

A real FFmpeg integration test generates a recording with two opposite-polarity graphics separated in time, extracts observations, and runs the complete pipeline through the discovery-pool option used by the UI, without pre-existing observation clips. It verifies temporal grouping, native extraction, the last-kept/first-kept conventions, retained manual-review status and an unchanged source digest. Synthetic reference positions are compared only after inference. Additional tests cover dual streaming with different crops and block boundaries, overlapping provenance without duplicate occurrences, single-hypothesis fallback, both-hypothesis failure, empty grouping and interruption/error stop conditions. Qt tests cover automatic launch without group selection, real child-process completion, partial and empty results, exact adjacent preview frames, confirmation, four-stage progress and reopening. Clip-count, hash and escaping-path checks run against real FFmpeg-produced observations.

The opening-transition search includes the anchor's first graphic frame: a jingle can begin exactly there. It does not search after that frame. This fixes a case exposed by the integration test; it is not a claim that all graphic starts are valid cuts.

## Reusing completed steps on retry

When the UI reuses the existing observation manifest, the coordinator also searches the repository's `tmp` for compatible completed scans and native exports. A scan is reusable only for the unchanged recording, the same observation paths/identities/SHA-256 digests, both-mode settings, persisted model-selection format, algorithm revision and complete ordered occurrence report. Current v2 learning checks complete training-peak edge shapes; earlier v1 and unversioned scans are incompatible and cannot bypass this check. Future algorithm changes must increment `GRAPHIC_ALGORITHM_REVISION`. Running, failed, differently parameterised or incompatible reports are skipped.

A native export additionally requires the exact scan digest, current source identity, exterior grouping and planned decoded windows. Every clip hash is verified. The new run copies only the frame map and required clips, verifies the copies and creates its own archive. It does not copy unrelated workspace files or accept a montage. Refinement then works on these short local clips. Report fields `reused_scan_from` and `reused_review_from` record provenance, and the UI indicates reuse.

This avoids repeating a full source scan and native source extraction when those stages already completed, including when only raccord interpretation was unresolved. It does not accelerate a first run or solve an ambiguous transition by itself. The explicit discovery-report route still prepares observations first; the UI's observation-manifest route reuses existing completed contexts. A real integration test runs twice and makes source scanning/extraction fail if called on the compatible retry; the second result must retain identical raccord candidates and an unchanged recording.
