def solve(haystack, needle):
    m = len(needle)
    fail = [0] * m
    j = 0
    for i in range(1, m):
        while j and needle[i] != needle[j]:
            j = fail[j - 1]
        if needle[i] == needle[j]:
            j += 1
        fail[i] = j
    j = 0
    for i, c in enumerate(haystack):
        while j and c != needle[j]:
            j = fail[j - 1]
        if c == needle[j]:
            j += 1
        if j == m:
            return i - m + 1
    return -1
