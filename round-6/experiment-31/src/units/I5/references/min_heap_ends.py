import heapq

def solve(intervals):
    intervals = sorted(intervals, key=lambda x: x[0])
    ends = []
    for s, e in intervals:
        if ends and ends[0] <= s:
            heapq.heappop(ends)
        heapq.heappush(ends, e)
    return len(ends)
