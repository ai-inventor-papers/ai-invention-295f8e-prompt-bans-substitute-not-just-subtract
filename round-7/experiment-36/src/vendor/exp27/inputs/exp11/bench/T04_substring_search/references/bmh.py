def solve(haystack, needle):
    n, m = len(haystack), len(needle)
    if m > n:
        return -1
    shift = {}
    for i in range(m - 1):
        shift[needle[i]] = m - 1 - i
    i = 0
    while i <= n - m:
        j = m - 1
        while j >= 0 and haystack[i + j] == needle[j]:
            j -= 1
        if j < 0:
            return i
        i += shift.get(haystack[i + m - 1], m)
    return -1
