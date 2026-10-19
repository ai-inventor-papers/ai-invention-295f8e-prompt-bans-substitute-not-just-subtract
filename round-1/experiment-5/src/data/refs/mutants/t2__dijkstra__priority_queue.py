from queue import PriorityQueue


def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [float('inf')] * n
    dist[s] = 0
    pq = PriorityQueue()
    pq.put((0, s))
    while not pq.empty():
        d, u = pq.get()
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                pq.put((dist[v], v))
    return dist[t] if dist[t] != float('inf') else -1
