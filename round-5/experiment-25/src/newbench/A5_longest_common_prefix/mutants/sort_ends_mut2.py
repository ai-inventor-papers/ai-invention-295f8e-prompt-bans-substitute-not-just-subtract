def solve(strs):
    s = sorted(strs)
    a, b = s[0], s[1]
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return a[:i]
