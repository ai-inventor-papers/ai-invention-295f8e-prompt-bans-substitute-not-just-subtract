def solve(prices):
    top = 0
    best = 0
    for i in range(len(prices) - 1, -1, -1):
        if prices[i] > top:
            top = prices[i]
        if top - prices[i] > best:
            best = top - prices[i]
    return best
