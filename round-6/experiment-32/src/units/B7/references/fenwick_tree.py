def solve(nums):
    ranks = {v: i + 1 for i, v in enumerate(sorted(set(nums)))}
    m = len(ranks)
    tree = [0] * (m + 1)
    inv = 0
    for k, v in enumerate(nums):
        r = ranks[v]
        s, i = 0, r
        while i > 0:
            s += tree[i]
            i -= i & -i
        inv += k - s
        i = r
        while i <= m:
            tree[i] += 1
            i += i & -i
    return inv
