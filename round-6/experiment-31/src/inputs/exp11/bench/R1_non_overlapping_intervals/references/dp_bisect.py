import bisect


def solve(intervals):
    iv = sorted(intervals, key=lambda x: x[1])
    ends = [e for _, e in iv]
    n = len(iv)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        s, e = iv[i - 1]
        j = bisect.bisect_right(ends, s, 0, i - 1)
        dp[i] = max(dp[i - 1], dp[j] + 1)
    return n - dp[n]
