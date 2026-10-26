def solve(n, roads):
    INF = float("inf")
    w = [[INF] * n for _ in range(n)]
    for u, v, c in roads:
        if c < w[u][v]:
            w[u][v] = w[v][u] = c
    dist = [INF] * n
    vis = [False] * n
    dist[0] = 0
    total = 0
    for _ in range(n):
        i = -1
        for j in range(n):
            if not vis[j] and (i == -1 or dist[j] < dist[i]):
                i = j
        if dist[i] == INF:
            return -1
        vis[i] = True
        total += dist[i]
        row = w[i]
        for j in range(n):
            if not vis[j] and row[j] < dist[j]:
                dist[j] = row[j]
    return total
