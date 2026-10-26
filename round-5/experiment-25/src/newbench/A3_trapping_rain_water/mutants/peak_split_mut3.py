def solve(height):
    n = len(height)
    peak = max(range(n), key=lambda i: height[i])
    water = 0
    m = 0
    for i in range(peak):
        m = max(m, height[i])
        water += m - height[i]
    return water
