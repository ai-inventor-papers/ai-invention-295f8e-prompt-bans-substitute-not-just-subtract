def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    INF = float("inf")
    dist = [INF] * n
    dist[s] = 0
    max_dist = 100 * n
    buckets = [[] for _ in range(100 * n + 1)]
    buckets[0].append(s)
    for d in range(max_dist + 1):
        bucket = buckets[d]
        while bucket:
            u = bucket.pop()
            if dist[u] != d:
                continue
            if u == t:
                return d
            for v, w in adj[u]:
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    buckets[nd].append(v)
    return -1 if dist[t] == INF else int(dist[t])
