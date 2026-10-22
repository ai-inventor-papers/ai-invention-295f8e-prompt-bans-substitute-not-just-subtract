def solve(height):
    n = len(height)
    left = [0] * n
    left[0] = height[0]
    for i in range(1, n):
        left[i] = max(left[i - 1], height[i])
    return sum(left[i] - height[i] for i in range(n))
