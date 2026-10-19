import heapq


def solve(n, edges, s, t):
    if s == t:
        return 0
    graph = {}
    for u, v, w in edges:
        graph.setdefault(u, []).append((v, w))
    dist = {s: 0}
    done = set()
    heap = [(0, s)]
    while heap:
        d, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        if u == t:
            return d
        for v, w in graph.get(u, []):
            if v not in done and d + w < dist.get(v, float('inf')):
                dist[v] = d + w
                heapq.heappush(heap, (d + w, v))
    return -1
