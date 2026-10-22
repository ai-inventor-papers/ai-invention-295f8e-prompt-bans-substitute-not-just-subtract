def solve(prices):
    low = prices[0]
    best = 0
    for p in prices:
        if p < low:
            low = p
        elif p - low > best:
            best = p - low
    return best
