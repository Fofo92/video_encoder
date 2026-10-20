# Graphic context around repeated motifs

Research diagnostic, not an editor proposal or a correction to the existing UI.

## Problem

Transitive local comparison can merge disjoint occurrences within one support
clip. The boundary refiner correctly rejects duplicate clip indices. Direct
comparisons to a common anchor avoid transitive bridging, but a shared core
may cover only an end logo. Core limits must not become cut points: preceding
animations may differ between otherwise matching support clips.

## Context measurement

`inspect_graphic_motif_context.py` reads existing extracted clips, validates
their frame counts and records their hashes in a local report. It identifies a
direct common core, then measures a contiguous graphic background around its
center. The background colour comes from that occurrence's median RGB; no named
colour or channel preset is used. Experimental thresholds are 40/255 maximum
channel distance, 80% pixel coverage, and a 2–10 second graphic region.
Observation-edge regions are rejected. These settings do not establish
separator semantics and have not been independently validated across captures.

## Reproduction without rereading the recording

```
python3 script/research/inspect_graphic_motif_context.py EXTRACTION_DIRECTORY \
  --output NEW_LOCAL_REPORT.json
```

The output must not already exist. The original manifest and video clips remain
unchanged. No project, queue job or encoding is produced. The report contains
local source provenance; review it before sharing.

## Remaining work

- Automatic family and role inference remains absent; this experiment consumes
  the families selected upstream.
- A flat background or repeated logo can occur in an advertisement or programme.
  The diagnostic always requires review and never treats these as proven cuts.
- Nonuniform jingles and smooth transitions can fail this measurement.
- Verify decoded/editor frame alignment and test independent captures before
  integrating it into the editor.
- The UI now offers a button to copy the diagnostic folder after a failed task;
  long traceback summaries remain bounded so action buttons stay accessible.

## Simplified selection in the experimental dialog

The default view now prepares a priority hypothesis without exposing group
selection. One common family with four interior occurrences, or two distinct
families with two/four alternating occurrences, can supply a hypothesis.
Recording-wide repetition support sets the search priority. This is not a
confidence estimate or proof of an advertisement. The view reports how many
other hypotheses remain. Equal support ties require arbitration rather than
silently using group order. The pilot does not select more than two ad ranges;
this is a workflow limit, not an assertion about broadcasting rules.

After loading discovery results, choose “Préparer les raccords à contrôler”.
Refinement must still succeed, followed by explicit review/confirmation before
replacing the in-memory montage. Group selection remains available under
advanced settings. No result means unresolved analysis, never proven absence
of advertisements. Discovery budget limits remain visible.

This UI change does not integrate the graphic-background experiment and does
not repair the known transitive local refinement failure. Existing encoding
jobs are unaffected. In particular, do not repeat a known failed refinement
solely to try the simplified selection.
