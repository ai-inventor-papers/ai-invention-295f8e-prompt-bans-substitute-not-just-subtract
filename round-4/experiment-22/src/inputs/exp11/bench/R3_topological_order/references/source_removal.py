def solve(n, prerequisites):
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for a, b in prerequisites:
        adj[b].append(a)
        indeg[a] += 1
    done = [False] * n
    order = []
    for _ in range(n):
        u = next((v for v in range(n) if not done[v] and indeg[v] == 0), -1)
        if u == -1:
            return []
        done[u] = True
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
    return order
