def solve(citations):
    n = len(citations)
    levels = [0] * (n + 1)
    for c in citations:
        if c >= n:
            levels[n] += 1
        else:
            levels[c] += 1
    total = 0
    for h in range(n, -1, -1):
        total += levels[h]
        if total >= h:
            return h
    return 0
