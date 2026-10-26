from collections import deque


def solve(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    INF = float('inf')
    dist = [INF] * n
    in_queue = [False] * n
    dist[s] = 0
    q = deque([s])
    in_queue[s] = True
    while q:
        u = q.popleft()
        in_queue[u] = False
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                if not in_queue[v]:
                    in_queue[v] = True
                    q.append(v)
    return -1 if dist[t] == INF else dist[t]
