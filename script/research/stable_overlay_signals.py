"""Shared persistent graphics in observation clips, not ad classification.

No channel identifier, reference times or hand-selected spatial region is used.
Clips themselves may be reference-selected: this is not full-source discovery.
"""
from collections import deque
import numpy as np

# Bump when learning or presence-scoring semantics change; old results must not be reused.
GRAPHIC_ALGORITHM_REVISION = 'shared-graphic-v2-peak-shapes'


def validate_frames(frames):
    if (frames.ndim != 4 or frames.shape[-1] != 3 or frames.dtype != np.uint8
            or not 5 <= frames.shape[0] <= 300
            or not 8 <= frames.shape[1] <= 360 or not 8 <= frames.shape[2] <= 640):
        raise ValueError('Expected 5 to 300 uint8 RGB frames, at most 640 by 360')


def white_edges(frames):
    validate_frames(frames)
    white = (frames.min(axis=3) >= 170) & (np.ptp(frames,axis=3) <= 70)
    eroded = np.zeros_like(white)
    interior = np.ones_like(white[:,2:-2,2:-2])
    for dy in range(5):
        for dx in range(5):
            interior &= white[:,dy:dy+interior.shape[1],dx:dx+interior.shape[2]]
    eroded[:,2:-2,2:-2] = interior
    edges = white & ~eroded
    # A clipped bright field is not evidence of an overlay at the image border.
    edges[:,:2] = False
    edges[:,-2:] = False
    edges[:,:,:2] = False
    edges[:,:,-2:] = False
    return edges


def contrast_edges(frames):
    """Local RGB contrast, invariant to RGB polarity inversion; no semantics."""
    validate_frames(frames)
    _,height,width,_ = frames.shape
    high,low = frames.copy(),frames.copy()
    for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
        target_y=slice(max(0,dy),min(height,height+dy))
        target_x=slice(max(0,dx),min(width,width+dx))
        source_y=slice(max(0,-dy),min(height,height-dy))
        source_x=slice(max(0,-dx),min(width,width-dx))
        neighbour=frames[:,source_y,source_x]
        np.maximum(high[:,target_y,target_x],neighbour,out=high[:,target_y,target_x])
        np.minimum(low[:,target_y,target_x],neighbour,out=low[:,target_y,target_x])
    edges=(high-low).max(axis=3)>=45
    edges[:,:2]=False;edges[:,-2:]=False
    edges[:,:,:2]=False;edges[:,:,-2:]=False
    return edges


def graphic_edges(frames, edge_mode='white'):
    if edge_mode == 'white':
        return white_edges(frames)
    if edge_mode == 'contrast':
        return contrast_edges(frames)
    raise ValueError('Unknown graphic edge mode')


def persistent_edges(frames, edge_mode='white'):
    edges = graphic_edges(frames,edge_mode)
    cumulative = np.concatenate([np.zeros((1,*edges.shape[1:]),dtype=np.uint16),
                                 edges.cumsum(axis=0,dtype=np.uint16)])
    # Five samples at 5 Hz; at least four must contain the same white edge.
    return np.any(cumulative[5:]-cumulative[:-5] >= 4,axis=0)


def shared_persistent_edges(clips, edge_mode='white'):
    if not 2 <= len(clips) <= 12:
        raise ValueError('Expected 2 to 12 observation clips')
    shape = clips[0].shape[1:]
    shared = None
    for clip in clips:
        if clip.shape[1:] != shape:
            raise ValueError('Observation clip dimensions differ')
        mask = persistent_edges(clip,edge_mode)
        shared = mask if shared is None else shared & mask
    return shared


def dilate(mask, radius=2):
    padded = np.pad(mask,radius)
    result = np.zeros_like(mask)
    h,w = mask.shape
    for y in range(2*radius+1):
        for x in range(2*radius+1):
            result |= padded[y:y+h,x:x+w]
    return result


def overlay_candidates(mask, minimum_support=20):
    if mask.ndim != 2 or mask.dtype != bool:
        raise ValueError('Expected a boolean shared-edge image')
    grown = dilate(mask)
    h,w = grown.shape
    remaining = set(map(int,np.flatnonzero(grown)))
    regions = []
    while remaining:
        seed = remaining.pop()
        queue = deque([seed]); pixels = []
        while queue:
            index = queue.popleft(); y,x = divmod(index,w); pixels.append((y,x))
            for ny,nx in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
                other = ny*w+nx
                if 0 <= ny < h and 0 <= nx < w and other in remaining:
                    remaining.remove(other);queue.append(other)
        ys,xs = zip(*pixels)
        x,y,x2,y2 = min(xs),min(ys),max(xs)+1,max(ys)+1
        support = int(mask[y:y2,x:x2].sum())
        if support >= minimum_support:
            regions.append({'bbox_xywh':[x,y,x2-x,y2-y],'shared_edge_pixels':support})
    return sorted(regions,key=lambda row:(-row['shared_edge_pixels'],row['bbox_xywh']))


def edge_presence_scores(edges, shared, bbox):
    x,y,w,h = bbox
    if edges.ndim != 3 or edges.dtype != bool or shared.shape != edges.shape[1:3] or w <= 0 or h <= 0 or x < 0 or y < 0 or x+w > shared.shape[1] or y+h > shared.shape[0]:
        raise ValueError('Template and observation geometry differ')
    positive = shared[y:y+h,x:x+w]
    if positive.sum() < 20:
        raise ValueError('Insufficient shared graphic support')
    negative = ~dilate(positive)
    if not negative.any():
        raise ValueError('No contrasting background around the shared graphic')
    region = edges[:,y:y+h,x:x+w]
    recall = region[:,positive].mean(axis=1)
    specificity = 1-region[:,negative].mean(axis=1)
    return (recall+specificity)/2


def presence_scores(frames, shared, bbox, edge_mode='white'):
    return edge_presence_scores(graphic_edges(frames,edge_mode),shared,bbox)


def peak_shape_agreement(clips, peaks, bbox, edge_mode='white'):
    """Compare complete peak edge shapes, not only their learned intersection.

    A few coincident edges in unrelated words/products can score highly against
    their own sparse intersection. Agreement is a training consistency check,
    never a separator classification or an independent validation sample.
    """
    if not 2 <= len(clips) <= 12 or len(peaks) != len(clips):
        raise ValueError('Expected a peak for each training observation')
    x,y,w,h = bbox
    masks=[]
    shape=clips[0].shape[1:]
    for clip,peak in zip(clips,peaks):
        validate_frames(clip)
        if (clip.shape[1:] != shape or type(peak) is not int or not 0<=peak<len(clip)
                or min(x,y)<0 or min(w,h)<=0 or x+w>shape[1] or y+h>shape[0]):
            raise ValueError('Invalid peak-shape comparison geometry')
        # Five-frame slice bounds memory; keep the exact selected sample.
        first=min(max(peak-2,0),len(clip)-5)
        mask=graphic_edges(clip[first:first+5],edge_mode)[peak-first]
        masks.append(mask[y:y+h,x:x+w])
    scores=[]
    for index,left in enumerate(masks):
        for right in masks[index+1:]:
            union=int((left|right).sum())
            scores.append(float((left&right).sum()/union) if union else 0.)
    return {'minimum_pairwise_iou':min(scores),'pairwise_iou':scores,
            'comparison':'full_peak_edges_in_learned_bbox; training_only'}


def refine_shared_candidate(clips, shared, bbox, rounds=2, edge_mode='white'):
    """Retain concurrently supported pixels; held-out clips must not be inputs."""
    if not 2 <= len(clips) <= 12 or type(rounds) is not int or not 1 <= rounds <= 3:
        raise ValueError('Expected 2 to 12 training clips and 1 to 3 refinement rounds')
    edges = [graphic_edges(clip,edge_mode) for clip in clips]
    x,y,w,h = bbox
    current = shared.copy()
    selected_samples = []
    for _ in range(rounds):
        consensus = None
        peaks = []
        for edge in edges:
            scores = edge_presence_scores(edge,current,bbox)
            peak = int(scores.argmax())
            peaks.append(peak)
            region = edge[max(0,peak-1):peak+2]
            if len(region) < 3:
                raise ValueError('Selected graphic is not bounded within an observation clip')
            stable = region.sum(axis=0) >= 2
            consensus = stable if consensus is None else consensus & stable
        current = np.zeros_like(shared)
        current[y:y+h,x:x+w] = consensus[y:y+h,x:x+w]
        if current.sum() < 20:
            raise ValueError('No sufficiently shared simultaneous graphic')
        selected_samples.append(peaks)
    return current, selected_samples
