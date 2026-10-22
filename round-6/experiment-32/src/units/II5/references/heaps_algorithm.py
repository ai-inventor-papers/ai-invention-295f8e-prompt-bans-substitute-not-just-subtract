def solve(nums):
    a = list(nums)
    n = len(a)
    c = [0] * n
    out = [a[:]]
    i = 0
    while i < n:
        if c[i] < i:
            if i % 2 == 0:
                a[0], a[i] = a[i], a[0]
            else:
                a[c[i]], a[i] = a[i], a[c[i]]
            out.append(a[:])
            c[i] += 1
            i = 0
        else:
            c[i] = 0
            i += 1
    return out
