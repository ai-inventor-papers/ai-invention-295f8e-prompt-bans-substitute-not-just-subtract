import heapq


def solve(n, edges, s, t):
    if s == t:
        return 0
    adj = [[] for _ in range(n)]
    radj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
        radj[v].append((u, w))
    INF = float("inf")
    dist_f = [INF] * n
    dist_b = [INF] * n
    dist_f[s] = 0
    dist_b[t] = 0
    heap_f = [(0, s)]
    heap_b = [(0, t)]
    done_f = [False] * n
    done_b = [False] * n
    mu = INF
    while heap_f and heap_b:
        if heap_f[0][0] + heap_b[0][0] >= mu:
            break
        if heap_f[0][0] <= heap_b[0][0]:
            d, u = heapq.heappop(heap_f)
            if done_f[u]:
                continue
            done_f[u] = True
            for v, w in adj[u]:
                if d + w < dist_f[v]:
                    dist_f[v] = d + w
                    heapq.heappush(heap_f, (d + w, v))
                if dist_b[v] < INF:
                    mu = min(mu, d + w + dist_b[v])
        else:
            d, u = heapq.heappop(heap_b)
            if done_b[u]:
                continue
            done_b[u] = True
            for v, w in radj[u]:
                if d + w < dist_b[v]:
                    dist_b[v] = d + w
                    heapq.heappush(heap_b, (d + w, v))
                if dist_f[v] < INF:
                    mu = min(mu, d + w + dist_f[v])
    return -1 if mu == INF else int(mu)
