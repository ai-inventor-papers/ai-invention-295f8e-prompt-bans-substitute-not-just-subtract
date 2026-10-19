def solve(n, edges, s, t):
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    max_d = 100 * (n - 1)
    INF = float('inf')
    dist = [INF] * n
    dist[s] = 0
    buckets = [[] for _ in range(max_d + 1)]
    buckets[0].append(s)
    for d in range(max_d + 1):
        b = buckets[d]
        i = 0
        while i < len(b):
            u = b[i]
            i += 1
            if dist[u] != d:
                continue
            if u == t:
                return d
            for v, w in adj[u]:
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    buckets[nd].append(v)
    return -1
