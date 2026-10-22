def solve(nums):
    n = len(nums)
    vis = [False] * n
    t = [0] * n
    ans = []

    def dfs(i):
        if i >= n:
            ans.append(t[:])
            return
        for j, x in enumerate(nums):
            if not vis[j]:
                vis[j] = True
                t[i] = x
                dfs(i + 1)
                vis[j] = False

    dfs(0)
    return ans
