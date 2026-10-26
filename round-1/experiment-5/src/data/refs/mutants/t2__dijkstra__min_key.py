def solve(n, edges, s, t):
    adj = {}
    for u, v, w in edges:
        adj.setdefault(u, []).append((v, w))
    dist = {i: float('inf') for i in range(n)}
    dist[s] = 0
    unvisited = set(range(n))
    while unvisited:
        u = min(unvisited, key=lambda x: dist[x])
        if dist[u] == float('inf'):
            break
        unvisited.remove(u)
        if u == t:
            break
        for v, w in adj.get(u, []):
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return dist[t] if dist[t] != float('inf') else -1
