def solve(prices):
    cur = best = 0
    for i in range(1, len(prices)):
        cur = max(0, cur + prices[i] - prices[i - 1])
        best = max(best, cur)
    return best
