def solve(intervals):
    import heapq
    intervals = sorted(intervals)
    ends = []
    for s, e in intervals:
        if ends and ends[0] < s:
            heapq.heappop(ends)
        heapq.heappush(ends, e)
    return len(ends)
