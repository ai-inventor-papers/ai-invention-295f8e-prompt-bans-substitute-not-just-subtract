def solve(intervals):
    iv = sorted(intervals)
    n = len(iv)
    longest = [1] * n
    for j in range(n):
        for i in range(j):
            if iv[i][1] <= iv[j][0] and longest[i] + 1 > longest[j]:
                longest[j] = longest[i] + 1
    return n - max(longest)
