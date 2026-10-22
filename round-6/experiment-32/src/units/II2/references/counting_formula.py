def solve(tasks, n):
    from collections import Counter
    cnt = Counter(tasks)
    x = max(cnt.values())
    s = sum(v == x for v in cnt.values())
    return max(len(tasks), (x - 1) * (n + 1) + s)
