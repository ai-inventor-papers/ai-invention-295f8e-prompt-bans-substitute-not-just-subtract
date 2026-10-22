def solve(points, k):
    return sorted(points, key=lambda p: abs(p[0]) + abs(p[1]))[:k]
