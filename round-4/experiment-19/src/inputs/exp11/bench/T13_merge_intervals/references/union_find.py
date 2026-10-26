def solve(intervals):
    n = len(intervals)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        si, ei = intervals[i]
        for j in range(i + 1, n):
            sj, ej = intervals[j]
            if si <= ej and sj <= ei:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    groups = {}
    for i in range(n):
        r = find(i)
        s, e = intervals[i]
        if r in groups:
            groups[r][0] = min(groups[r][0], s)
            groups[r][1] = max(groups[r][1], e)
        else:
            groups[r] = [s, e]
    return sorted(groups.values())
