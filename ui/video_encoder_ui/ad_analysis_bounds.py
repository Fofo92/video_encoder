def ad_analysis_bounds(session, source_id, first, last, length):
    """Use explicit markers, or the single saved segment after markers reset."""
    if first is None and last is None:
        segments = session.segments
        if len(segments) != 1 or segments[0].source_id != source_id:
            return None
        first, last = segments[0].start_frame, segments[0].end_frame

    if first is None or last is None or not 0 <= first < last < length:
        return None
    return first, last
