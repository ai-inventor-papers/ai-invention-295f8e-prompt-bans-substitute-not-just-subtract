import heapq

def solve(n, roads):
    adj = [[] for _ in range(n)]
    for u, v, w in roads:
        adj[u].append((w, v))
        adj[v].append((w, u))
    seen = [False] * n
    heap = [(0, 0)]
    total = 0
    count = 0
    while heap and count < n:
        w, u = heapq.heappop(heap)
        if seen[u]:
            continue
        seen[u] = True
        total += w
        count += 1
        for e in adj[u]:
            if not seen[e[1]]:
                heapq.heappush(heap, e)
    return total if count == n else -1
