def solve(n, prerequisites):
    adj = [[] for _ in range(n)]
    for a, b in prerequisites:
        adj[b].append(a)
    color = [0] * n
    post = []

    def dfs(u):
        color[u] = 1
        for v in adj[u]:
            if color[v] == 1:
                return False
            if color[v] == 0 and not dfs(v):
                return False
        color[u] = 2
        post.append(u)
        return True

    for u in range(n):
        if color[u] == 0 and not dfs(u):
            return []
    return post[::-1]
