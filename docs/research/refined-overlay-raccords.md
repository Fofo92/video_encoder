# Candidate raccords from decoded-index review clips

`script/research/refine_overlay_review.py` refines the windows produced by `prepare_overlay_review.py`. A completed 25 fps export and matching clip hashes are required. It reads only review clips, not the original recording. Candidate pairs, file paths, disjoint decoded index intervals, frame counts and manifest stability are checked. Windows are currently limited to 600 frames; default 400-frame review exports are supported.

```sh
python3 script/research/refine_overlay_review.py \
  --review tmp/decoded-review \
  --output tmp/new-candidate-raccords.json
```

Reference cuts are not inputs. The approximate graphic location and duration identify a bounded transition search interval. Image differences retain alternatives and black-entry/exit evidence. A dominant entry into black, two transitions with a strongest/runner-up ratio below 1.5, or no qualifying transition remain unresolved. These heuristics do not classify programme content or establish that a pause contains only advertising. Candidate output always requires review.

For a departure transition at decoded index N, the candidate last kept image is N−1. For a resume transition at decoded index N, the candidate first kept image is N. Tests explicitly protect this asymmetry. The candidate status is not acceptance: no montage, project, database or encoding queue is written. The JSON output must not already exist.

Source-index mapping comes from the extraction manifest. Equality with editor coordinates is not assumed by the module. Human reference positions may be compared in a separate evaluation after inference; this does not establish accuracy on independent recordings, especially when the discovery graphic was learned from selected observations of the same recording. Confirmation in the editor remains a separate step before using any candidate in an accepted montage.
