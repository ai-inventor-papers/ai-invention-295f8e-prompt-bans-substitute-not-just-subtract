from collections import defaultdict


def solve(n, edges, s, t):
    graph = defaultdict(list)
    for u, v, w in edges:
        graph[u].append((v, w))
    dist = {s: 0}
    buckets = defaultdict(list)
    buckets[0].append(s)
    pending = 1
    current = 0
    done = set()
    while pending:
        while not buckets.get(current):
            buckets.pop(current, None)
            current += 1
        bucket = buckets[current]
        u = bucket.pop()
        pending -= 1
        if u in done or dist.get(u) != current:
            continue
        done.add(u)
        if u == t:
            return current
        for v, w in graph[u]:
            nd = current + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                buckets[nd].append(v)
                pending += 1
    return -1
