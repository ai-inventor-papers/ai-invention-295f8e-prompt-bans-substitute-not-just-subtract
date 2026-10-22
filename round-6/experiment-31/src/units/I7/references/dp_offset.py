def solve(n):
    ans = [0] * (n + 1)
    p = 1
    for i in range(1, n + 1):
        if p * 2 == i:
            p = i
        ans[i] = ans[i - p] + 1
    return ans
