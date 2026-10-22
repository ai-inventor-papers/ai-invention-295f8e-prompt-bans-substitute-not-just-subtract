def solve(points, k):
    import heapq
    h = []
    for x, y in points:
        d = -(x * x + y * y)
        if len(h) < k:
            heapq.heappush(h, (d, x, y))
        elif d > h[0][0]:
            heapq.heapreplace(h, (d, x, y))
    return [[x, y] for _, x, y in h]
