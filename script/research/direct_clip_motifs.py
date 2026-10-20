"""Find a common core by direct anchor matches, never transitive components."""
import numpy as np
from repeated_visual_sequences import motion_scores, window_scores
from direct_motif_groups import window_contrast


def discover(features, sample_fps=5, window_seconds=2, max_rmse=15):
    window = round(sample_fps * window_seconds)
    if len(features) < 3 or any(len(value) < window for value in features):
        return []
    motion = [motion_scores(value, window) for value in features]
    contrast = [window_contrast(value, window) for value in features]
    scores = [window_scores(features[0], value, window) for value in features[1:]]
    choices = []
    for anchor in np.flatnonzero(motion[0] >= 2):
        starts, errors = [int(anchor)], []
        for index, matrix in enumerate(scores, 1):
            values = matrix[anchor]
            scale = np.sqrt((contrast[0][anchor] + contrast[index]) / 2) * 255
            accepted = ((values <= max_rmse) & (motion[index] >= 2)
                        & (values <= .5 * scale) & (scale > 0))
            matches = np.flatnonzero(accepted)
            # Multiple separated matches are ambiguous; do not silently pick one.
            if not len(matches) or np.any(np.diff(matches) > window):
                break
            best = int(matches[np.argmin(values[matches])])
            starts.append(best)
            errors.append(float(values[best]))
        if len(starts) == len(features):
            choices.append((max(errors), starts))
    if not choices:
        return []
    choices.sort(key=lambda row: row[0])
    starts = choices[0][1]
    if any(any(abs(a - b) > window for a, b in zip(starts, other)) for _, other in choices):
        return []
    return [{'supporting_clips': len(features),
             'grouping': 'direct_common_anchor',
             'occurrences': [{'clip_index': index, 'core_start_seconds': start / sample_fps,
                              'core_end_seconds': (start + window) / sample_fps}
                             for index, start in enumerate(starts)]}]
