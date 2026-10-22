import heapq

def solve(citations):
    heap = [-c for c in citations]
    heapq.heapify(heap)
    h = 0
    while heap:
        c = -heapq.heappop(heap)
        if c >= h + 1:
            h += 1
        else:
            break
    return h
