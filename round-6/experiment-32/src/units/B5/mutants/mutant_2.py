from itertools import combinations

def solve(nums):
    out = []
    for r in range(1, len(nums) + 1):
        out.extend(list(c) for c in combinations(nums, r))
    return out
