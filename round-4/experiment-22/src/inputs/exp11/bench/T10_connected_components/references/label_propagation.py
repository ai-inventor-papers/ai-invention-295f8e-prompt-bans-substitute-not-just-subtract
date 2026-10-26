def solve(n, edges):
    label = list(range(n))
    changed = True
    while changed:
        changed = False
        for u, v in edges:
            m = min(label[u], label[v])
            if label[u] != m:
                label[u] = m
                changed = True
            if label[v] != m:
                label[v] = m
                changed = True
    return len(set(label))
