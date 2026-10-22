def solve(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = [False] * n

    def dfs(u, parent):
        seen[u] = True
        for v in adj[u]:
            if v == parent:
                continue
            if seen[v] or dfs(v, u):
                return True
        return False

    for s in range(n):
        if not seen[s] and dfs(s, -1):
            return True
    return False
