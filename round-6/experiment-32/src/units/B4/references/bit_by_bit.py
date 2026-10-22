def solve(x):
    res = 0
    for b in range(16, -1, -1):
        cand = res | (1 << b)
        if cand * cand <= x:
            res = cand
    return res
