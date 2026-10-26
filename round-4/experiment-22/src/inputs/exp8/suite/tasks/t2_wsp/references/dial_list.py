def solve(n, edges, s, t):
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    max_w = 0
    for u, v, w in edges:
        adj[u].append((v, w))
        max_w = max(max_w, w)
    INF = float('inf')
    dist = [INF] * n
    dist[s] = 0
    max_dist = max_w * (n - 1)
    buckets = [[] for _ in range(max_dist + 1)]
    buckets[0].append(s)
    idx = 0
    while idx <= max_dist:
        if not buckets[idx]:
            idx += 1
            continue
        u = buckets[idx].pop()
        if dist[u] != idx:
            continue
        if u == t:
            return idx
        for v, w in adj[u]:
            nd = idx + w
            if nd <= max_dist and nd < dist[v]:
                dist[v] = nd
                buckets[nd].append(v)
    return -1 if dist[t] == INF else dist[t]
