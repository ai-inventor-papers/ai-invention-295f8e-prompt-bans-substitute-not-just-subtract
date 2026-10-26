def solve(height):
    stack = []
    water = 0
    for i, h in enumerate(height):
        while stack and height[stack[-1]] < h:
            bottom = stack.pop()
            if not stack:
                break
            left = stack[-1]
            water += min(height[left], h) - height[bottom]
        stack.append(i)
    return water
