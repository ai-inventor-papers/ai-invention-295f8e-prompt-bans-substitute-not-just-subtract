def solve(intervals):
    events = []
    for s, e in intervals:
        events.append((s, 1))
        events.append((e, -1))
    events.sort(key=lambda x: (x[0], -x[1]))
    cur = best = 0
    for _, d in events:
        cur += d
        best = max(best, cur)
    return best
