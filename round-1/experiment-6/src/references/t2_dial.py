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
    limit = max_w * max(n - 1, 1) + 1
    buckets = [[] for _ in range(limit + 1)]
    buckets[0].append(s)
    done = [False] * n
    for d in range(limit + 1):
        bucket = buckets[d]
        while bucket:
            u = bucket.pop()
            if done[u] or dist[u] != d:
                continue
            done[u] = True
            if u == t:
                return d
            for v, w in adj[u]:
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    buckets[nd].append(v)
    return -1
