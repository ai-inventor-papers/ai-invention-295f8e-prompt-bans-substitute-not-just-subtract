import random


def solve(nums, k):
    a = list(nums)
    t = k - 1
    lo, hi = 0, len(a) - 1
    while lo < hi:
        pivot = a[random.randint(lo, hi)]
        lt, i, gt = lo, lo, hi
        while i <= gt:
            if a[i] < pivot:
                a[lt], a[i] = a[i], a[lt]
                lt += 1
                i += 1
            elif a[i] > pivot:
                a[gt], a[i] = a[i], a[gt]
                gt -= 1
            else:
                i += 1
        if t < lt:
            hi = lt - 1
        elif t > gt:
            lo = gt + 1
        else:
            return a[t]
    return a[lo]
