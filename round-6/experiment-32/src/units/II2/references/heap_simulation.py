def solve(tasks, n):
    import heapq
    from collections import Counter
    heap = [-c for c in Counter(tasks).values()]
    heapq.heapify(heap)
    time = 0
    while heap:
        tmp = []
        for _ in range(n + 1):
            if heap:
                tmp.append(heapq.heappop(heap))
        for c in tmp:
            if c + 1 < 0:
                heapq.heappush(heap, c + 1)
        time += n + 1 if heap else len(tmp)
    return time
