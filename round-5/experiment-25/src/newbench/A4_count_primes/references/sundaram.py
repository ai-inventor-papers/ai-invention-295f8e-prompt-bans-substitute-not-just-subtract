def solve(n):
    if n < 3:
        return 0
    k = (n - 2) // 2
    marked = [False] * (k + 1)
    i = 1
    while i + i + 2 * i * i <= k:
        j = i
        while i + j + 2 * i * j <= k:
            marked[i + j + 2 * i * j] = True
            j += 1
        i += 1
    count = 1
    for m in range(1, k + 1):
        if not marked[m] and 2 * m + 1 < n:
            count += 1
    return count
