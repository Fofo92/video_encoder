# Conditional review from an existing framing cache

Before learning graphics, the simplified coordinator checks for a sealed cache
of the unchanged source: already decoded 32x18 RGB samples at five Hz. Identity,
dimensions, SHA-256 and manifest are verified. Missing, changed or unsuitable
caches leave the graphic route available. First discovery still needs decoding.

This is a conditional format hypothesis, not an advertising classification.
Bilateral-band classification must cover half the programme, with at least 75%
of known samples letterboxed. Five-second local occupancy requires ten known
samples and 80% letterbox support; holes up to five seconds are bridged. Anchors
last 120 seconds. Between anchors, 30 seconds of positively full-frame pixels
must constitute half of known samples. Mixed evidence or excursions over 900
seconds remain unresolved. Darkness alone cannot establish a pause. No expected
pause count, channel, brand, project or interior reference position is an input.

The last letterboxed sample before full-frame evidence brackets a departure; the
last full-frame sample and first following letterboxed sample bracket a return.
A later long anchor does not postpone that first return when overlays temporarily
obscure the bands. Six seconds of context on either side produce native windows,
clamped to exterior bounds. Overlap, width over 600 frames or more than six pairs
prevents a complete set. A first native review still reads the recording once to
extract these windows; the expensive graphic presence scan is skipped. Compatible
native exports are reused after verifying the report digest, grouping, windows,
source identity and every clip checksum.

Native refinement requires one transition of the expected direction within four
seconds of the coarse bracket, states sustained 0.4 seconds and at most two
seconds of unknown pixels between states. A distinct visual change in that
bracket proposes the last-kept or first-kept frame; weak or competing changes
remain unresolved. `review_origin: format_hypotheses` uses the same source, bounds,
frame convention, manifest and unchecked-confirmation validation as the graphic
route. Preparation modifies no project, source or encoding queue.

## Supplied recording evaluation

Expendables 4 has 38997 cached samples. All 67386816 bytes match SHA-256
`5d8ff6b2d51d26f29611b3ca15f38140eb09cba7f49551e8d148d3c62e3c345a`.
Inside exterior frames 11019..161908, 25597 samples are letterboxed, 2600 full-frame
and 1981 unknown. The planner receives no reference project:

| Role | Sampled bracket, seconds | Window [first, end exclusive) | Reference kept frame |
| --- | --- | --- | --- |
| Departure 1 | 2291.4–2291.6 | [57135, 57441) | 57255 |
| Return 1 | 2626.2–2626.4 | [65505, 65811) | 65626 |
| Departure 2 | 4535.2–4535.4 | [113230, 113536) | 113344 |
| Return 2 | 4896.4–4896.6 | [122260, 122566) | 122380 |

All four windows contain the subsequently compared references. Coarse centres
are about 1.2–1.5 seconds after the native/editor references. Source/editor
alignment remains unverified: these sampled values are not exact cuts. Native
Expendables refinement has not yet been exercised; previously supplied native
clips contain advertisements at different positions. Development used this
recording: this is an in-sample improvement, not independent accuracy evidence.
The unchanged planner abstains on Aquaman (34.2% of known samples letterboxed),
leaving the graphic route available. Film framing changes, short pauses and
letterboxed advertisements remain limitations requiring visual review.

Six focused tests cover zero/one/two/three excursions, darkness and full-frame
abstention, delayed anchors, clipping, mixed/overlong evidence, native kept-frame
conventions and sealed-cache integrity without a decoder. A real FFmpeg test
generates a 420-second recording, extracts and refines its windows, verifies the
exact frame references afterwards and fails if a graphic source scan is called.
The retry fails if native extraction is called again, requires the same review
result and checks the unchanged source digest. UI tests cover the format origin,
unchecked initial confirmation and current-source validation.

## Manual adjustment after reviewing a candidate

In the separator dialog, navigating with the frame field or the one-frame
buttons changes the preview only. The explicit **Retenir cette image pour le
raccord** action changes the selected proposal. The displayed edge determines
the convention: last-kept OUT / first-discarded for a departure, last-discarded /
first-kept IN for a return. The helper validates the full ordered montage against
current source identity and exterior bounds before updating the proposal.

Edited rows show **ajusté**, keep their revised positions when reselected and
clear the confirmation checkbox. The user reviews, confirms again and chooses
**Remplacer le montage**; the revised segments then enter the main editor and are
saved through its normal project workflow. Closing the dialog without replacing
the montage discards these in-dialog edits. Preview movement itself never changes
a cut. The dialog attempts one bounded seek correction when the reader returns
a neighbouring frame. It then synchronizes the frame field, preview and retained
coordinate to the actual known position, as the main editor does; signals are
blocked during this synchronization to prevent recursive seeking. A valid nearby
image is no longer rejected merely because it differs from the requested index.
Unavailable images or unknown positions still disable adjustment. The button
tooltip explains calculation, selection, incomplete-proposal or preview blockers.

This works for format, graphic and legacy motif proposals. Invalid moves retain
the previous valid proposal. The common apply dispatcher handles both geometric
origins, including format results. Tests exercise the complete dialog-to-montage
path and the Expendables regression: proposed OUT 113349 manually changed to
113346 becomes the inclusive OUT of segment 2. Reference corrections do not
change detector timing or introduce a fixed global offset.

Reader-offset tests cover a consistent one-frame seek offset, a nearby known
position that cannot be corrected exactly, and an unknown position. They verify
that navigation leaves the proposal unchanged and explicit adjustment retains
the displayed coordinate. Selecting an occurrence decodes only once before any
bounded offset correction, avoiding the former duplicate preview request.

## Completing unresolved boundaries manually

A partial review lists every expected departure and return, including missing
limits marked **à renseigner**. Selecting one preserves the navigation cursor;
it does not invent a cut coordinate. Navigate to the desired image, select the
last-kept OUT or first-kept IN convention, and explicitly retain that image.

Available limits remain ordered and inside the exterior bounds. Each retained
limit records its original report index and previous coordinate (null for a
missing limit). When the final missing limit is supplied, the complete montage
is validated before confirmation becomes available. Explicit confirmation and
**Remplacer le montage** are still required. Save the project in the main editor
to preserve these edits; no analysis is rerun and diagnostic files stay unchanged.
