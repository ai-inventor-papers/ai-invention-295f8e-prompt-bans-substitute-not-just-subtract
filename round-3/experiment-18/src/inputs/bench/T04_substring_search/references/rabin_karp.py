def solve(haystack, needle):
    n, m = len(haystack), len(needle)
    if m > n:
        return -1
    base, mod = 256, 1_000_000_007
    hn = hw = 0
    for i in range(m):
        hn = (hn * base + ord(needle[i])) % mod
        hw = (hw * base + ord(haystack[i])) % mod
    high = pow(base, m - 1, mod)
    for i in range(n - m + 1):
        if hn == hw and haystack[i:i + m] == needle:
            return i
        if i + m < n:
            hw = ((hw - ord(haystack[i]) * high) * base + ord(haystack[i + m])) % mod
    return -1
