def solve(nums):
    a = list(nums)
    out = []

    def go(i):
        if i == len(a):
            out.append(a[:])
            return
        for j in range(i, len(a)):
            a[i], a[j] = a[j], a[i]
            go(i + 1)

    go(0)
    return out
