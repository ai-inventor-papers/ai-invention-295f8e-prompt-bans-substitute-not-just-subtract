def solve(s):
    best = s[:1]
    n = len(s)
    for c in range(n):
        l = r = c
        while l >= 0 and r < n and s[l] == s[r]:
            l -= 1
            r += 1
        if r - l - 1 > len(best):
            best = s[l + 1:r]
    return best
