def solve(nums):
    ranks = {v: i + 1 for i, v in enumerate(sorted(set(nums)))}
    m = len(ranks)
    tree = [0] * (m + 1)
    best = 0
    for x in nums:
        r = ranks[x] - 1
        q = 0
        while r > 0:
            if tree[r] > q:
                q = tree[r]
            r -= r & -r
        cur = q + 1
        if cur > best:
            best = cur
        i = ranks[x]
        while i <= m:
            if tree[i] < cur:
                tree[i] = cur
            i += i & -i
    return best
