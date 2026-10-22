def solve(prices):
    low = prices[0]
    best = 0
    for p in prices:
        low = min(low, p)
        best = max(best, low - p)
    return best
