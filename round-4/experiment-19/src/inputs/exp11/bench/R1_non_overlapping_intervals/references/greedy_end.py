def solve(intervals):
    kept = 0
    last_end = None
    for s, e in sorted(intervals, key=lambda iv: iv[1]):
        if last_end is None or s >= last_end:
            kept += 1
            last_end = e
    return len(intervals) - kept
