import heapq
from collections import Counter


def solve(nums, k):
    counts = Counter(nums)
    heap = []
    for v, c in counts.items():
        heapq.heappush(heap, (c, v))
        if len(heap) > k:
            heapq.heappop(heap)
    return [v for _, v in heap]
