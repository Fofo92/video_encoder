# Stable overlay signals in observation clips

`script/research/stable_overlay_signals.py` is a research module for shared white graphics over changing backgrounds. It accepts RGB observation arrays, not a channel identity, logo template, spatial region or reference cut positions. Inputs are bounded to 5–300 samples per clip, at most 640×360 pixels, and 2–12 clips of matching dimensions. Samples are assumed to be at five frames per second.

The module retains near-white edges, excluding the image border and the interior of large white fields. For each clip it finds edges present at the same position in at least four samples of a five-sample window. It then intersects this evidence across clips and finds connected spatial regions. Candidate regions are ordered by their shared-edge support, not by a claim that they are advertising logos. Every detected shared graphic remains unclassified.

`refine_shared_candidate` selects peak matches in the training clips, then retains pixels simultaneously supported in those observations. It uses a fixed number of rounds and rejects insufficient support or a peak clipped by an observation boundary. Held-out clips must never be passed into refinement. This limits background contamination, but does not remove the selection bias of the input observations.

`presence_scores` measures coverage of the learned edges and absence of edges in the immediately surrounding region. Its output is an exploratory similarity score, not a calibrated probability. A graphic may appear after the start of a jingle, and its disappearance may not give the first frame to keep. Neither score nor candidate region produces a cut.

A useful evaluation holds out one observation clip, learns regions on the others, and measures presence in the held-out clip. This tests transfer between selected observations, **not independent full-recording accuracy**. Even without explicit cut coordinates, observations extracted around known junctions introduce selection bias. Shared title cards, subtitles, programme graphics and recurring advertisement elements may also qualify. Dark, coloured, moving or relocated logos can be missed. The module must not be used as an automatic montage rule.

The existing UI, source sampling, detector thresholds and encoding queue are unchanged. No captured images, learned channel-specific template or private recording metadata are part of the repository.

## Polarity-invariant contrast hypothesis

The research scanner also accepts `--edge-mode contrast`; the default remains `white`. This alternative takes the maximum local RGB range over the centre pixel and its four direct neighbours, keeping contrast of at least 45/255. It is invariant to replacing every RGB value by `255-value`, so an inverted graphic may retain the same contours. It does not use a channel name, a logo template or a hand-selected region. Persistence, shared-region refinement and sustained-presence requirements remain the same. The selected mode is recorded in the model and scan report and is used again during presence scoring.

In a four-observation leave-one-out check, the contrast hypothesis recovered a late-jingle fragment in all four colour-inverted observations, where the white hypothesis had three training abstentions and one held-out miss. It also recovered a fragment in all four observations of the translucent moving style. On the original changing-background style, however, two contrast trainings abstained and two transferred; the white hypothesis had transferred in all four. Neither mode is a universal replacement for the other. Contrast also admitted much larger regions in the moving-style observations, which warrants full-recording false-positive checks before any promotion.

These checks concern selected observation clips from existing recordings. They do not establish independent accuracy, full-source specificity, complete jingle bounds or exact cut coordinates. A late graphic fragment may be several seconds after the start of the jingle; do not assume the current native boundary search necessarily reaches that start. No UI choice, automatic fallback, montage or queue operation is introduced by this research option.

## Cross-habillage check

The [integrated research runner](integrated-graphic-review.md) now tries both hypotheses automatically. `scan_stable_overlays.py --edge-mode both` exposes the same combined scan for research use. Source pixels are decoded once, overlapping detections retain both origins, and a failed training hypothesis does not suppress another valid hypothesis. No detector choice is added to the main UI.

Before treating this signal as a general jingle detector, repeat the observation-level evaluation with unchanged thresholds on other graphic styles. For four observations, learn on three and score the fourth, rotating the held-out clip. Report training abstentions, missing held-out detections and misplaced detections separately. A training peak alone is not a successful transfer.

Colour-inverted departure/resume animations and translucent moving lettering are important negative cases for a near-white, fixed-position edge model. A programme's persistent corner logo can also be the shared graphic. Do not compensate by selecting a channel-specific region or by using the reviewed cut coordinates. Keep animation/motif evidence available; this white-graphic signal is one hypothesis, not a replacement for the other research paths.

Legacy observation containers with incomplete frame counts may be used to inspect decoded visual evidence, but must not enter the strict native raccord refiner or support claims about source/editor frame accuracy. Full-recording false positives and independent captures remain separate validation requirements.

An initial cross-style observation check produced two different outcomes with the same settings: one four-clip set yielded a short late-jingle fragment in all four held-out observations; a colour-inverted set yielded three training abstentions and one held-out miss. The first outcome establishes local visual transfer only: a late fragment does not locate the start of the jingle, and neither set establishes full-recording specificity. These are selected observations, not independent source-only benchmarks.
