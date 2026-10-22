def solve(nums):
    parent = {}
    size = {}
    for v in nums:
        if v not in parent:
            parent[v] = v
            size[v] = 1

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]

    for v in list(parent):
        if v + 1 in parent:
            union(v, v + 1)
    return max((size[find(v)] for v in parent), default=0)
