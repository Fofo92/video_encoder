# Transition evidence around a graphic anchor

`script/research/jingle_boundary_signals.py` examines an observation-local half-open graphic-presence interval. It does not locate the graphic, classify a separator or accept a montage. Input is bounded to 600 RGB samples at at most 320×180; the sampling rate and search bounds are explicit.

The module retains distinct strong image changes in a bounded interval before the anchor and around its disappearance. A transition is described as a visual change, entry into a dark field, or exit from a dark field. These labels describe pixels, not programme semantics. The strongest pre-anchor transition and its runner-up are both preserved; their ratio is descriptive evidence, not calibrated confidence.

An internal jingle edit can be stronger than its opening. An advertisement-to-black transition can also outrank the following black-to-jingle transition. Therefore selecting the nearest or strongest transition alone is not an accepted boundary rule. The module always requires manual review and emits no source frame conversion, cut decision or edit project.

Observation clips sampled at ten frames per second cannot prove single-frame precision for a 25-frame-per-second editor. FFmpeg seek times also do not establish original decoded/editor frame indices. Reference-cut evaluation must keep this distinction explicit and must not convert local seconds into trusted source frame numbers.

Existing detector defaults, UI and encoding jobs remain unchanged. This diagnostic is used to inspect which additional evidence is needed before proposing complete jingle intervals.
