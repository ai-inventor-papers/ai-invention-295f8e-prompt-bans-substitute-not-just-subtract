import heapq


def solve(nums, k):
    h = list(nums)
    heapq.heapify(h)
    for _ in range(k - 1):
        heapq.heappop(h)
    return h[0]
