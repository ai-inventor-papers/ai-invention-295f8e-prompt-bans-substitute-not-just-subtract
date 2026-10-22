def solve(points, k):
    import random
    pts = [list(p) for p in points]
    dist = lambda p: p[0] * p[0] + p[1] * p[1]
    lo, hi = 0, len(pts) - 1
    rng = random.Random(0)
    while lo < hi:
        piv = dist(pts[rng.randint(lo, hi)])
        i, j = lo, hi
        while i <= j:
            while dist(pts[i]) < piv:
                i += 1
            while dist(pts[j]) > piv:
                j -= 1
            if i <= j:
                pts[i], pts[j] = pts[j], pts[i]
                i += 1
                j -= 1
        if k - 1 <= j:
            hi = j
        elif k - 1 >= i:
            lo = i
        else:
            break
    return pts[:k]
