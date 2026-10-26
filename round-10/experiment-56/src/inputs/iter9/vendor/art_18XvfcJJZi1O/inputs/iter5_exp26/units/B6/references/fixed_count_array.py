def solve(s, t):
    if len(s) != len(t):
        return False
    cnt = [0] * 26
    for c in s:
        cnt[ord(c) - 97] += 1
    for c in t:
        cnt[ord(c) - 97] -= 1
    return all(v == 0 for v in cnt)
