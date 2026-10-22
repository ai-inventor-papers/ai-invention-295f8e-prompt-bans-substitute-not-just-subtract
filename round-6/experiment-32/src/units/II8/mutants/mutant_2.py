def solve(points, k):
    return sorted(points, key=lambda p: p[0] * p[0] + p[1] * p[1])[:k - 1] or points[:1]
