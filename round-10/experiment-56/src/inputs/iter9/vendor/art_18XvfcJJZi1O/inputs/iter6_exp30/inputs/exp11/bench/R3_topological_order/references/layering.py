def solve(n, prerequisites):
    depth = [0] * n
    for _ in range(n):
        changed = False
        for a, b in prerequisites:
            if depth[b] + 1 > depth[a]:
                depth[a] = depth[b] + 1
                changed = True
        if not changed:
            return sorted(range(n), key=lambda u: depth[u])
    return []
