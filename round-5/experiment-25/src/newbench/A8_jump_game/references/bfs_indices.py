from collections import deque


def solve(nums):
    n = len(nums)
    seen = [False] * n
    seen[0] = True
    q = deque([0])
    far = 0
    while q:
        i = q.popleft()
        if i == n - 1:
            return True
        for j in range(max(i + 1, far + 1), min(n, i + nums[i] + 1)):
            if not seen[j]:
                seen[j] = True
                q.append(j)
        far = max(far, i + nums[i])
    return False
