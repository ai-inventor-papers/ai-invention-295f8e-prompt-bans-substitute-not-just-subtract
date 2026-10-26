def solve(s, t):
    if len(s) != len(t):
        return False
    d = {}
    for c in s:
        d[c] = d.get(c, 0) + 1
    for c in t:
        if d.get(c, 0) == 0:
            return False
        d[c] -= 1
    return True
