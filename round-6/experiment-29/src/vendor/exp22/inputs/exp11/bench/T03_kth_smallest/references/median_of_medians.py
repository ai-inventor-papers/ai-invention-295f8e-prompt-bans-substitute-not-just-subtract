def solve(nums, k):
    def select(a, t):
        if len(a) <= 5:
            return sorted(a)[t]
        groups = [a[i:i + 5] for i in range(0, len(a), 5)]
        medians = [sorted(g)[len(g) // 2] for g in groups]
        pivot = select(medians, len(medians) // 2)
        lows = [x for x in a if x < pivot]
        highs = [x for x in a if x > pivot]
        n_eq = len(a) - len(lows) - len(highs)
        if t < len(lows):
            return select(lows, t)
        if t < len(lows) + n_eq:
            return pivot
        return select(highs, t - len(lows) - n_eq)

    return select(list(nums), k - 1)
