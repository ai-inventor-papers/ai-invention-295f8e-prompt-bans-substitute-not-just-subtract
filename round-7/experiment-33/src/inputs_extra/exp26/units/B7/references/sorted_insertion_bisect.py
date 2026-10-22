from bisect import bisect_right, insort

def solve(nums):
    seen = []
    inv = 0
    for k, v in enumerate(nums):
        inv += k - bisect_right(seen, v)
        insort(seen, v)
    return inv
