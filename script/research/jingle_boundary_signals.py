"""Transition evidence near an observation-local graphic anchor, never cut decisions."""
import math
import numpy as np


def boundary_evidence(frames, anchor, fps=10., lookback_seconds=4., end_radius_seconds=.6):
    if (frames.ndim != 4 or frames.shape[-1] != 3 or frames.dtype != np.uint8
            or not 2 <= len(frames) <= 600 or frames.shape[1] > 180 or frames.shape[2] > 320
            or not frames.shape[1] or not frames.shape[2]):
        raise ValueError('Expected bounded uint8 RGB observation frames, at most 320 by 180')
    if (not math.isfinite(fps) or fps <= 0 or not math.isfinite(lookback_seconds)
            or not 0 < lookback_seconds <= 10 or not math.isfinite(end_radius_seconds)
            or not 0 < end_radius_seconds <= 2):
        raise ValueError('Invalid sampling rate or observation search bounds')
    first,last = anchor
    if (type(first) is not int or type(last) is not int or not 0 <= first < last <= len(frames)):
        raise ValueError('Anchor must be an observation-local half-open frame range')
    pixels = frames.astype(np.float32)
    difference = np.mean(np.abs(np.diff(pixels,axis=0)),axis=(1,2,3))
    luma = .2126*pixels[:,:,:,0]+.7152*pixels[:,:,:,1]+.0722*pixels[:,:,:,2]
    black = (luma.mean(axis=(1,2)) <= 8) & (np.mean(luma <= 20,axis=(1,2)) >= .99)

    def candidates(low,high,limit=5):
        # Transition i is between observation frames i-1 and i.
        indices = range(max(1,low),min(len(frames),high))
        ranked = sorted(indices,key=lambda i:(-difference[i-1],i))
        selected = []
        for index in ranked:
            if difference[index-1] < 20:
                break
            if any(abs(index-row['observation_frame']) < max(1,round(.3*fps)) for row in selected):
                continue
            kind = ('exit_black' if black[index-1] and not black[index]
                    else 'enter_black' if not black[index-1] and black[index] else 'visual_change')
            selected.append({'observation_frame':int(index),'seconds':index/fps,
                             'pixel_change':float(difference[index-1]),'kind':kind})
            if len(selected) == limit:
                break
        return selected

    # The first graphic frame can itself be the first jingle frame.
    opening = candidates(first-round(lookback_seconds*fps),first+1)
    radius = max(1,round(end_radius_seconds*fps))
    closing = candidates(last-radius,last+radius+1)
    dominance = (opening[0]['pixel_change']/opening[1]['pixel_change'] if len(opening)>1
                 else None)
    return {'status':'observation_transition_evidence','needs_manual_review':True,
            'opening_candidates':opening,'closing_candidates':closing,
            'opening_strongest_to_runner_up_ratio':dominance,
            'coordinate_basis':'Observation-local sampled frames; source/editor mapping unverified',
            'limitations':['A visual change may occur inside a jingle or advertisement',
                           'Black detection does not classify a jingle',
                           'Graphic presence is not a complete jingle interval',
                           'No source frame conversion, cut decision or edit project']}
