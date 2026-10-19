"""Leave one excerpt out of motif discovery, then search it without its labels.

This is within-sample validation, not validation on an unseen recording.
"""

import numpy as np

from repeated_visual_sequences import discover, motion_scores, window_scores


def evaluate(features, min_clips=3):
    if len(features) <= min_clips:
        return {"status": "unavailable", "reason": "Need more clips than the discovery support requirement"}
    results = []
    for withheld, target in enumerate(features):
        training = [frames for index, frames in enumerate(features) if index != withheld]
        candidates = discover(training, min_clips=min_clips)
        matches = []
        for index, candidate in enumerate(candidates):
            occurrence = candidate["occurrences"][0]
            center = (occurrence["core_start_seconds"] + occurrence["core_end_seconds"]) / 2
            first = max(0, round((center - 1) * 5))
            template = training[occurrence["clip_index"]][first:first + 10]
            if len(template) != 10:
                continue
            scores = window_scores(template, target, 10)
            if not scores.size:
                continue
            hits = np.flatnonzero((scores[0] <= 15) & (motion_scores(target, 10) >= 2))
            for run in np.split(hits, np.flatnonzero(np.diff(hits) > 1) + 1):
                if len(run):
                    matches.append({"training_candidate_index": index, "core_start_seconds": int(run[0]) / 5,
                                    "core_end_seconds": (int(run[-1]) + 10) / 5,
                                    "best_rmse": round(float(scores[0, run].min()), 3)})
        results.append({"withheld_clip_index": withheld, "training_candidates": len(candidates),
                        "matches": matches, "needs_manual_review": True})
    return {"status": "experimental", "protocol": "leave_one_excerpt_out_same_sample",
            "semantic_status": "Matches do not establish separator semantics", "results": results}
