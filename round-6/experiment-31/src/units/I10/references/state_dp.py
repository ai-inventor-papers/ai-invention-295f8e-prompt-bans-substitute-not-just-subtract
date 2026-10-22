def solve(prices):
    hold = -prices[0]
    sold = 0
    for p in prices[1:]:
        sold = max(sold, hold + p)
        hold = max(hold, -p)
    return sold
