# Stable overlay signals in observation clips

`script/research/stable_overlay_signals.py` is a research module for shared white graphics over changing backgrounds. It accepts RGB observation arrays, not a channel identity, logo template, spatial region or reference cut positions. Inputs are bounded to 5–300 samples per clip, at most 640×360 pixels, and 2–12 clips of matching dimensions. Samples are assumed to be at five frames per second.

The module retains near-white edges, excluding the image border and the interior of large white fields. For each clip it finds edges present at the same position in at least four samples of a five-sample window. It then intersects this evidence across clips and finds connected spatial regions. Candidate regions are ordered by their shared-edge support, not by a claim that they are advertising logos. Every detected shared graphic remains unclassified.

`refine_shared_candidate` selects peak matches in the training clips, then retains pixels simultaneously supported in those observations. It uses a fixed number of rounds and rejects insufficient support or a peak clipped by an observation boundary. Held-out clips must never be passed into refinement. This limits background contamination, but does not remove the selection bias of the input observations.

`presence_scores` measures coverage of the learned edges and absence of edges in the immediately surrounding region. Its output is an exploratory similarity score, not a calibrated probability. A graphic may appear after the start of a jingle, and its disappearance may not give the first frame to keep. Neither score nor candidate region produces a cut.

A useful evaluation holds out one observation clip, learns regions on the others, and measures presence in the held-out clip. This tests transfer between selected observations, **not independent full-recording accuracy**. Even without explicit cut coordinates, observations extracted around known junctions introduce selection bias. Shared title cards, subtitles, programme graphics and recurring advertisement elements may also qualify. Dark, coloured, moving or relocated logos can be missed. The module must not be used as an automatic montage rule.

The existing UI, source sampling, detector thresholds and encoding queue are unchanged. No captured images, learned channel-specific template or private recording metadata are part of the repository.

## Cross-habillage check

Before treating this signal as a general jingle detector, repeat the observation-level evaluation with unchanged thresholds on other graphic styles. For four observations, learn on three and score the fourth, rotating the held-out clip. Report training abstentions, missing held-out detections and misplaced detections separately. A training peak alone is not a successful transfer.

Colour-inverted departure/resume animations and translucent moving lettering are important negative cases for a near-white, fixed-position edge model. A programme's persistent corner logo can also be the shared graphic. Do not compensate by selecting a channel-specific region or by using the reviewed cut coordinates. Keep animation/motif evidence available; this white-graphic signal is one hypothesis, not a replacement for the other research paths.

Legacy observation containers with incomplete frame counts may be used to inspect decoded visual evidence, but must not enter the strict native raccord refiner or support claims about source/editor frame accuracy. Full-recording false positives and independent captures remain separate validation requirements.

An initial cross-style observation check produced two different outcomes with the same settings: one four-clip set yielded a short late-jingle fragment in all four held-out observations; a colour-inverted set yielded three training abstentions and one held-out miss. The first outcome establishes local visual transfer only: a late fragment does not locate the start of the jingle, and neither set establishes full-recording specificity. These are selected observations, not independent source-only benchmarks.
