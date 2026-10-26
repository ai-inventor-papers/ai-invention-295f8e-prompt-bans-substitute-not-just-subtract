from collections import deque


def solve(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    parent = [-2] * n
    for s in range(n):
        if parent[s] != -2:
            continue
        parent[s] = -1
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v == parent[u]:
                    continue
                if parent[v] != -2:
                    return True
                parent[v] = u
                q.append(v)
    return False
