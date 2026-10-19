import heapq


def solve(n, edges, s, t):
    if s == t:
        return 0
    fwd = [[] for _ in range(n)]
    rev = [[] for _ in range(n)]
    for u, v, w in edges:
        fwd[u].append((v, w))
        rev[v].append((u, w))
    INF = float('inf')
    df, db = {s: 0}, {t: 0}
    pf, pb = [(0, s)], [(0, t)]
    done_f, done_b = set(), set()
    best = INF
    while pf and pb:
        if pf[0][0] + pb[0][0] >= best:
            break
        if pf[0][0] <= pb[0][0]:
            d, u = heapq.heappop(pf)
            if u in done_f:
                continue
            done_f.add(u)
            for v, w in fwd[u]:
                nd = d + w
                if nd < df.get(v, INF):
                    df[v] = nd
                    heapq.heappush(pf, (nd, v))
                if v in db and nd + db[v] < best:
                    best = nd + db[v]
        else:
            d, u = heapq.heappop(pb)
            if u in done_b:
                continue
            done_b.add(u)
            for v, w in rev[u]:
                nd = d + w
                if nd < db.get(v, INF):
                    db[v] = nd
                    heapq.heappush(pb, (nd, v))
                if v in df and nd + df[v] < best:
                    best = nd + df[v]
    return best if best != INF else -1
