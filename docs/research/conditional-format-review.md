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
