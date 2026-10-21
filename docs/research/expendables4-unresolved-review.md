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
the discrepancies. Neither successful learning nor agreement between
white and contrast hypotheses establishes that the graphic is an advertising
separator rather than part of a repeated advertisement.

Important distinction: initial **observation** windows are training context;
they need not contain a film boundary. Final **refinement** windows must contain
the boundary to propose it. Comparing references with initial observations alone
does not establish the cause of failure. Here the final manifests are available
and establish a localization problem under the stated coordinate assumption.

Do not tune transition thresholds or expand all windows from these reference
positions. This would not establish a source-independent detector and would
increase decoding cost. The report-only collector deliberately omits pixels; the explicit
`--include-review-clips` option collects the hashed clips referenced by the last
pipeline's two manifests, including observations extracted in a previous run.
It never starts a decoder, reads the recording or touches the encoding queue.
Unrelated MP4/MKV files are not included. Modified clips or manifests fail before
the archive is created. Collector tests cover report-only behavior, exact
clip selection, cross-run observations, tampering and bounded collection.

## Pixel inspection and learning guard

The subsequently supplied observation and native-review clips were inspected.
Three training peaks show a repeated LU/Pim's product shot; the remaining peak
shows a Burger King advertisement. The learned sparse intersection scores both
highly despite their different full edge patterns. Final clips show advertising
content throughout their sampled views; the learned product graphic is not a
verified channel separator. The original full recording has not been accessed.

The learner now compares all pairs of full peak edge masks in its selected
bounding box. An intersection-over-union below 0.20 in any pair causes abstention
before scanning the full source. Only already selected training peaks are used;
no reference boundary, brand name, channel template, text recognition or fixed
screen region is an input. The minimum pairwise overlaps measured on the supplied
observation clips are:

| Recording | White edges | Contrast edges |
| --- | --- | --- |
| Expendables 4 | 0.090 | 0.133 |
| Aquaman | 0.491 | 0.495 |
| Chien & Chat | 0.776 | 0.473 |
| Braveheart | Existing learning abstention | 0.805 |

This small, in-sample comparison supports rejecting the contradictory
Expendables training set while retaining the established successful hypotheses.
It does not calibrate a universal threshold or measure independent detection
accuracy. Consistently repeated advertisements can still pass; a passed guard is
not a separator classification. The check uses five-frame slices around the
selected peaks and does not add full-recording decoding.

If neither hypothesis can be learned, the scan and coordinator now return a
normal `needs_review` result with an explicit French reason, zero recording
samples and no extraction/refinement. Decoder tests fail if the full source is
opened for decoding in that path. Genuine decoder errors remain failures. The
algorithm revision is incremented to `shared-graphic-v2-peak-shapes`, so previous
v1 scan caches cannot bypass the check. Compatible v2 retries still reuse scans
and native exports.

To research the missing separators, existing crops of advertisements are not
enough: the full-source low-resolution discovery cache is needed. The collector's
explicit `--include-discovery-cache` option includes that existing sealed cache
and its manifest only when source identity, frame count, size, local path and
SHA-256 agree. It starts no decoding and fails if no compatible cache exists.
