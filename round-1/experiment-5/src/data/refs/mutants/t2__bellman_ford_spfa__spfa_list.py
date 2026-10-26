def solve(n, edges, s, t):
    graph = {i: [] for i in range(n)}
    for u, v, w in edges:
        graph[u].append((v, w))
    dist = [float('inf')] * n
    dist[s] = 0
    queue = [s]
    inq = {s}
    while queue:
        u = queue.pop(0)
        inq.discard(u)
        for v, w in graph[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                if v not in inq:
                    queue.append(v)
                    inq.add(v)
    return -1 if dist[t] == float('inf') else dist[t]
