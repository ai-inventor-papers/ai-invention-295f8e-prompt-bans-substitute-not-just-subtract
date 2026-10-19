def solve(n, edges, s, t):
    INF = float('inf')
    w_min = [[INF] * n for _ in range(n)]
    for u, v, w in edges:
        if w < w_min[u][v]:
            w_min[u][v] = w
    dist = [INF] * n
    dist[s] = 0
    done = [False] * n
    for _ in range(n):
        u = -1
        best = INF
        for i in range(n):
            if not done[i] and dist[i] < best:
                best = dist[i]
                u = i
        if u == -1:
            break
        done[u] = True
        row = w_min[u]
        for v in range(n):
            if row[v] != INF and dist[u] + row[v] < dist[v]:
                dist[v] = dist[u] + row[v]
    return dist[t] if dist[t] != INF else -1
