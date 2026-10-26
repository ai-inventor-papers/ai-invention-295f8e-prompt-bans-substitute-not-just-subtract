import heapq
import itertools


def solve(n, edges, s, t):
    graph = {}
    for u, v, w in edges:
        graph.setdefault(u, []).append((v, w))
    entry_finder = {}
    pq = []
    counter = itertools.count()
    REMOVED = -1

    def add_or_update(node, priority):
        if node in entry_finder:
            entry_finder[node][-1] = REMOVED
        entry = [priority, next(counter), node]
        entry_finder[node] = entry
        heapq.heappush(pq, entry)

    dist = {s: 0}
    visited = set()
    add_or_update(s, 0)
    while pq:
        priority, _, node = heapq.heappop(pq)
        if node == REMOVED:
            continue
        del entry_finder[node]
        visited.add(node)
        if node == t:
            return priority
        for v, w in graph.get(node, []):
            if v in visited:
                continue
            nd = priority + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                add_or_update(v, nd)
    return -1
