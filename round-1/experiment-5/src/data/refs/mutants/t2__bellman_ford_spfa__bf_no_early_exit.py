def solve(n, edges, s, t):
    INF = 10**18
    d = [INF] * n
    d[s] = 0
    for i in range(n - 1):
        for (u, v, w) in edges:
            if d[u] < INF and d[u] + w < d[v]:
                d[v] = d[u] + w
    return d[t] if d[t] < INF else -1
