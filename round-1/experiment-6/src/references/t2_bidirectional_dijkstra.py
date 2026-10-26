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
    dist_f = {s: 0}
    dist_b = {t: 0}
    heap_f = [(0, s)]
    heap_b = [(0, t)]
    done_f, done_b = set(), set()
    best = INF
    while heap_f and heap_b:
        if heap_f[0][0] + heap_b[0][0] >= best:
            break
        if heap_f[0][0] <= heap_b[0][0]:
            d, u = heapq.heappop(heap_f)
            if u in done_f:
                continue
            done_f.add(u)
            for v, w in fwd[u]:
                nd = d + w
                if nd < dist_f.get(v, INF):
                    dist_f[v] = nd
                    heapq.heappush(heap_f, (nd, v))
                if v in dist_b:
                    best = min(best, nd + dist_b[v])
        else:
            d, u = heapq.heappop(heap_b)
            if u in done_b:
                continue
            done_b.add(u)
            for v, w in rev[u]:
                nd = d + w
                if nd < dist_b.get(v, INF):
                    dist_b[v] = nd
                    heapq.heappush(heap_b, (nd, v))
                if v in dist_f:
                    best = min(best, nd + dist_f[v])
    return best if best < INF else -1
