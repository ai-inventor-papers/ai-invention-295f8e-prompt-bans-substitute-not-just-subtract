from bisect import bisect_left, insort

def solve(nums):
    seen = []
    inv = 0
    for k, v in enumerate(nums):
        inv += k - bisect_left(seen, v)
        insort(seen, v)
    return inv
