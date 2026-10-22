def solve(nums):
    n = len(nums)
    seen = [False] * (n + 2)
    for v in nums:
        if 1 <= v <= n + 1:
            seen[v] = True
    for k in range(1, n + 2):
        if not seen[k]:
            return k
    return n + 2
