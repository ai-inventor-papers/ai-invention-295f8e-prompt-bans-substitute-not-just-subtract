from collections import deque


def solve(nums):
    n = len(nums)
    q = deque([0])
    seen = {0}
    while q:
        i = q.popleft()
        j = i + nums[i]
        if j >= n - 1:
            return True
        if j not in seen:
            seen.add(j)
            q.append(j)
    return False
