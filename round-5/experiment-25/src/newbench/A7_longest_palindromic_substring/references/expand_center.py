def solve(s):
    best_l, best_r = 0, 0
    n = len(s)
    for c in range(2 * n - 1):
        l, r = c // 2, c // 2 + c % 2
        while l >= 0 and r < n and s[l] == s[r]:
            l -= 1
            r += 1
        if r - l - 1 > best_r - best_l:
            best_l, best_r = l + 1, r
    return s[best_l:best_r]
