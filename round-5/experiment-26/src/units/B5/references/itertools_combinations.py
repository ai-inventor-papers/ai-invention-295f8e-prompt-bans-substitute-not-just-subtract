from itertools import combinations

def solve(nums):
    out = []
    for r in range(len(nums) + 1):
        out.extend(list(c) for c in combinations(nums, r))
    return out
