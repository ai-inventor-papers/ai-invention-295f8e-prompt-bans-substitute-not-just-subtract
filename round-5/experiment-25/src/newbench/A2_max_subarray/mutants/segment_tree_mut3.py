def solve(nums):
    n = len(nums)
    size = 1
    while size < n:
        size *= 2
    best = [None] * (2 * size)
    for i, x in enumerate(nums):
        best[size + i] = x
    for j in range(size - 1, 0, -1):
        a, b = best[2 * j], best[2 * j + 1]
        best[j] = a if b is None else (b if a is None else max(a, b))
    return best[1]
