import heapq


def solve(n, edges, s, t):
    if s == t:
        return 0
    fwd = [[] for _ in range(n)]
    bwd = [[] for _ in range(n)]
    for u, v, w in edges:
        fwd[u].append((v, w))
        bwd[v].append((u, w))
    INF = float('inf')
    dist_f = [INF] * n
    dist_b = [INF] * n
    dist_f[s] = 0
    dist_b[t] = 0
    pq_f = [(0, s)]
    pq_b = [(0, t)]
    done_f = [False] * n
    done_b = [False] * n
    best = INF
    while pq_f and pq_b:
        if pq_f[0][0] + pq_b[0][0] >= best:
            break
        if pq_f[0][0] <= pq_b[0][0]:
            d, u = heapq.heappop(pq_f)
            if done_f[u]:
                continue
            done_f[u] = True
            for v, w in fwd[u]:
                if d + w < dist_f[v]:
                    dist_f[v] = d + w
                    heapq.heappush(pq_f, (d + w, v))
                if dist_b[v] < INF:
                    best = min(best, d + w + dist_b[v])
        else:
            d, u = heapq.heappop(pq_b)
            if done_b[u]:
                continue
            done_b[u] = True
            for v, w in bwd[u]:
                if d + w < dist_b[v]:
                    dist_b[v] = d + w
                    heapq.heappush(pq_b, (d + w, v))
                if dist_f[v] < INF:
                    best = min(best, d + w + dist_f[v])
    return best if best < INF else -1
