def solve(n, roads):
    p = list(range(n))
    def find(x):
        while p[x] != x:
            x = p[x]
        return x
    ans = 0
    for x, y, c in sorted(roads, key=lambda r: r[2]):
        a, b = find(x), find(y)
        if a != b:
            p[a] = b
            ans += c
    return ans
