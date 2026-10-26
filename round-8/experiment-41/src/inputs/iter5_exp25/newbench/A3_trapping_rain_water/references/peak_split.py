def solve(height):
    n = len(height)
    peak = 0
    for i in range(n):
        if height[i] > height[peak]:
            peak = i
    water = 0
    m = 0
    for i in range(peak):
        if height[i] > m:
            m = height[i]
        else:
            water += m - height[i]
    m = 0
    for i in range(n - 1, peak, -1):
        if height[i] > m:
            m = height[i]
        else:
            water += m - height[i]
    return water
