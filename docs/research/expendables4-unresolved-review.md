# Expendables 4: completed computation, unresolved boundaries

The 2026-10-21 diagnostic contains a completed five-Hz, white/contrast graphic
scan (38997 samples, 413 seconds) and a normally completed pipeline (516 seconds).
Two temporal groups contain four graphic occurrences. Native refinement abstains
on all four roles: competing transitions, no transition, competing transitions,
and entry into black. This is not a stalled background calculation.

The manually corrected project was supplied afterwards. Its interior kept-frame
references are 57255, 65626, 113344 and 122380. They were not inputs to discovery,
learning, scanning, grouping or refinement. The final extraction windows are:

| Role | Decoded window [first, end exclusive) | Reference | Reference outside window by |
| --- | --- | --- | --- |
| Departure 1 | [58585, 58985) | 57255 | 53.20 s |
| Resume 1 | [64210, 64610) | 65626 | 40.68 s |
| Departure 2 | [118685, 119085) | 113344 | 213.64 s |
| Resume 2 | [120885, 121285) | 122380 | 43.84 s |

These comparisons assume the unverified source/editor coordinate mapping. A
constant offset cannot explain the opposite signs and differing magnitudes of
the discrepancies. The original recording and observation pixels have not yet
been inspected for this case. Neither successful learning nor agreement between
white and contrast hypotheses establishes that the graphic is an advertising
separator rather than part of a repeated advertisement.

Important distinction: initial **observation** windows are training context;
they need not contain a film boundary. Final **refinement** windows must contain
the boundary to propose it. Comparing references with initial observations alone
does not establish the cause of failure. Here the final manifests are available
and establish a localization problem under the stated coordinate assumption.

Do not tune transition thresholds or expand all windows from these reference
positions. This would not establish a source-independent detector and would
increase decoding cost. Inspect the existing observation and native-review clips
first. The report-only collector deliberately omits pixels; the explicit
`--include-review-clips` option collects the hashed clips referenced by the last
pipeline's two manifests, including observations extracted in a previous run.
It never starts a decoder, reads the recording or touches the encoding queue.
Unrelated MP4/MKV files are not included. Modified clips or manifests fail before
the archive is created. Five collector tests cover report-only behavior, exact
clip selection, cross-run observations, tampering and bounded collection.
