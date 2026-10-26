def solve(n, edges):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    count = n
    for u, v in edges:
        a, b = find(u), find(v)
        if a != b:
            parent[a] = b
            count -= 1
    return count
