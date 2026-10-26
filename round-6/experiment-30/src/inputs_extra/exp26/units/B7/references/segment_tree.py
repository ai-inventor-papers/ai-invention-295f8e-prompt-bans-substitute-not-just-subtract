def solve(nums):
    vals = sorted(set(nums))
    rank = {v: i for i, v in enumerate(vals)}
    m = len(vals)
    tree = [0] * (4 * m)
    def update(node, lo, hi, pos):
        tree[node] += 1
        if lo == hi:
            return
        mid = (lo + hi) // 2
        if pos <= mid:
            update(2 * node, lo, mid, pos)
        else:
            update(2 * node + 1, mid + 1, hi, pos)
    def query(node, lo, hi, l, r):
        if r < lo or hi < l or l > r:
            return 0
        if l <= lo and hi <= r:
            return tree[node]
        mid = (lo + hi) // 2
        return query(2 * node, lo, mid, l, r) + query(2 * node + 1, mid + 1, hi, l, r)
    inv = 0
    for v in nums:
        p = rank[v]
        inv += query(1, 0, m - 1, p + 1, m - 1)
        update(1, 0, m - 1, p)
    return inv
