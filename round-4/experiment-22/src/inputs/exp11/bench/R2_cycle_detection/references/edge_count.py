def solve(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    comp = [-1] * n
    c = 0
    for s in range(n):
        if comp[s] != -1:
            continue
        comp[s] = c
        stack = [s]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if comp[v] == -1:
                    comp[v] = c
                    stack.append(v)
        c += 1
    nodes = [0] * c
    edge_cnt = [0] * c
    for u in range(n):
        nodes[comp[u]] += 1
    for u, v in edges:
        edge_cnt[comp[u]] += 1
    return any(edge_cnt[i] >= nodes[i] for i in range(c))
