def solve(nums):
    length = {}
    best = 0
    for v in nums:
        if v in length:
            continue
        left = length.get(v - 1, 0)
        right = length.get(v + 1, 0)
        total = left + right + 1
        length[v] = total
        length[v - left] = total
        length[v + right] = total
        best = max(best, total)
    return best
