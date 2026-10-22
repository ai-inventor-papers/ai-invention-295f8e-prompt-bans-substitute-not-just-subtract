def solve(s, t):
    from bisect import bisect_left
    pos = {}
    for i, ch in enumerate(t):
        pos.setdefault(ch, []).append(i)
    cur = 0
    for c in s:
        lst = pos.get(c)
        if not lst:
            return False
        j = bisect_left(lst, cur)
        if j == len(lst):
            return False
        cur = lst[j] + 1
    return True
