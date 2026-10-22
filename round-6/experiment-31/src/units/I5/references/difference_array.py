def solve(intervals):
    top = max(e for _, e in intervals)
    diff = [0] * (top + 2)
    for s, e in intervals:
        diff[s] += 1
        diff[e] -= 1
    cur = best = 0
    for d in diff:
        cur += d
        best = max(best, cur)
    return best
