def solve(nums):
    from itertools import permutations
    return [list(p) for p in permutations(nums)]
