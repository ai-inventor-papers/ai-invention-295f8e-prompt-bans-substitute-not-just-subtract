from heapq import heappush, heappop


def solve(n, edges, s, t):
    if s == t:
        return 0
    forward = {}
    backward = {}
    for u, v, w in edges:
        forward.setdefault(u, []).append((v, w))
        backward.setdefault(v, []).append((u, w))
    dist = [{s: 0}, {t: 0}]
    heaps = [[(0, s)], [(0, t)]]
    settled = [set(), set()]
    graphs = [forward, backward]
    mu = float('inf')
    side = 0
    while heaps[0] and heaps[1]:
        if heaps[0][0][0] + heaps[1][0][0] >= mu:
            break
        d, u = heappop(heaps[side])
        if u not in settled[side] and d <= dist[side].get(u, float('inf')):
            settled[side].add(u)
            other = 1 - side
            for v, w in graphs[side].get(u, []):
                nd = d + w
                if nd < dist[side].get(v, float('inf')):
                    dist[side][v] = nd
                    heappush(heaps[side], (nd, v))
                if v in dist[other]:
                    mu = min(mu, nd + dist[other][v])
            if u in dist[other]:
                mu = min(mu, d + dist[other][u])
        side = 1 - side
    return mu if mu != float('inf') else -1
