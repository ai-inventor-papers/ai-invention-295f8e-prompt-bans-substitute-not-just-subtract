def solve(n, roads):
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    comps = n
    total = 0
    while comps > 1:
        cheapest = [-1] * n
        for idx, (u, v, w) in enumerate(roads):
            a, b = find(u), find(v)
            if a == b:
                continue
            if cheapest[a] == -1 or w < roads[cheapest[a]][2]:
                cheapest[a] = idx
            if cheapest[b] == -1 or w < roads[cheapest[b]][2]:
                cheapest[b] = idx
        merged = False
        for c in range(n):
            if cheapest[c] != -1:
                u, v, w = roads[cheapest[c]]
                a, b = find(u), find(v)
                if a != b:
                    parent[a] = b
                    total += w
                    comps -= 1
                    merged = True
        if not merged:
            return -1
    return total
