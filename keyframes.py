"""Select enclosing keyframe bounds from a bounded ffprobe scan."""

import math


def snap_interval(frames, start, end, duration, offset=0.0, scan_seconds=30):
    if not all(math.isfinite(x) for x in (start, end, duration, offset)):
        raise ValueError("Video timestamps must be finite")
    if not 0 <= start < end <= duration:
        raise ValueError("Choose an in point before the out point")
    times = set()
    for frame in frames:
        value = float(frame["best_effort_timestamp_time"]) - offset
        if not math.isfinite(value):
            raise ValueError("Invalid keyframe timestamp")
        if -0.001 <= value <= duration:
            times.add(max(0.0, value))
    earlier = [time for time in times if time <= start + 0.000001]
    later = [time for time in times if time >= end - 0.000001]
    if end + scan_seconds >= duration:
        later.append(duration)
    if not earlier or not later:
        raise ValueError("No nearby enclosing keyframes were found; use another range")
    return max(earlier), min(later)
