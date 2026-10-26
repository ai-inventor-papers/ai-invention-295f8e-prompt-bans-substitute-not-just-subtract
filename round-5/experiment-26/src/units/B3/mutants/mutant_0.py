def solve(n, roads):
    ws = sorted(r[2] for r in roads)
    return sum(ws[:n - 1]) if len(ws) >= n - 1 else -1
