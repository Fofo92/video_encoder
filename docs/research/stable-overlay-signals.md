# Stable overlay signals in observation clips

`script/research/stable_overlay_signals.py` is a research module for shared white graphics over changing backgrounds. It accepts RGB observation arrays, not a channel identity, logo template, spatial region or reference cut positions. Inputs are bounded to 5–300 samples per clip, at most 640×360 pixels, and 2–12 clips of matching dimensions. Samples are assumed to be at five frames per second.

The module retains near-white edges, excluding the image border and the interior of large white fields. For each clip it finds edges present at the same position in at least four samples of a five-sample window. It then intersects this evidence across clips and finds connected spatial regions. Candidate regions are ordered by their shared-edge support, not by a claim that they are advertising logos. Every detected shared graphic remains unclassified.

`refine_shared_candidate` selects peak matches in the training clips, then retains pixels simultaneously supported in those observations. It uses a fixed number of rounds and rejects insufficient support or a peak clipped by an observation boundary. Held-out clips must never be passed into refinement. This limits background contamination, but does not remove the selection bias of the input observations.

`presence_scores` measures coverage of the learned edges and absence of edges in the immediately surrounding region. Its output is an exploratory similarity score, not a calibrated probability. A graphic may appear after the start of a jingle, and its disappearance may not give the first frame to keep. Neither score nor candidate region produces a cut.

A useful evaluation holds out one observation clip, learns regions on the others, and measures presence in the held-out clip. This tests transfer between selected observations, **not independent full-recording accuracy**. Even without explicit cut coordinates, observations extracted around known junctions introduce selection bias. Shared title cards, subtitles, programme graphics and recurring advertisement elements may also qualify. Dark, coloured, moving or relocated logos can be missed. The module must not be used as an automatic montage rule.

The existing UI, source sampling, detector thresholds and encoding queue are unchanged. No captured images, learned channel-specific template or private recording metadata are part of the repository.
